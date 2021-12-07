import torch
import torch.nn.functional as F
import torch.optim as optim
from sklearn.metrics import f1_score, roc_auc_score
from scipy.sparse import coo_matrix
import numpy as np
from torch_geometric.utils import convert

def flipAdj(edge_idx: torch.Tensor,i,j,n):
    # TODO: check if it's efficient enough

    # i,j : edit idx
    # n, num of node in graph
    # edge_idx : torch_tensor, shape [m,2]. m = num of existing edges

    # restore the sparse mat
    data = np.ones(edge_idx.shape[1])
    t_mat = coo_matrix((data,edge_idx.numpy()),shape=(n,n)).tocsr()

    # flip 
    if (t_mat[i,j] == 0):
        t_mat[i,j] = 1.
        t_mat[j,i] = 1.
    else:
        t_mat[i,j] = 0.
        t_mat[j,i] = 0.

    # Change back
    return convert.from_scipy_sparse_matrix(t_mat)[0]

class bf_trainer():
    def __init__(self, sense_idx, numEdit, model=None, dataset=None, optimizer=None, features=None, edge_index=None, 
                    labels=None, device=None, train_idx=None, val_idx=None, fair_metric = None):
        self.model = model
        self.sense_idx = sense_idx # int, which attribute dimension is sensitive?
        self.numEdit = numEdit # number of edges that we plan to edit
        self.model_name = model.model_name
        self.dataset = dataset
        self.optimizer = optimizer
        self.features = features
        self.edge_index = edge_index
        self.labels = labels
        self.device = device
        self.train_idx = train_idx
        self.val_idx = val_idx
        self.numNode = features.shape[0]
        # From nifty
        counter_features = features.clone()
        counter_features[:, sense_idx] = 1 - counter_features[:, sense_idx]
        self.counter_features = counter_features
    

    def train(self, epochs=200):

        best_loss = 100
        best_acc = 0

        for epoch in range(epochs):
            ## TODO: Perform a search over all edge edits within each neighborhood of a node to find one that helps fairness
            # You will need to bring over the fairness metrics (make it be able to use any metric we choose) and then brute force search 

#           One normal step in training
            self.model.train()
            self.optimizer.zero_grad()
            output = self.model(self.features, self.edge_index)
            # Binary Cross-Entropy  
            preds = (output.squeeze()>0).type_as(self.labels)
            loss_train = F.binary_cross_entropy_with_logits(output[self.train_idx], self.labels[self.train_idx].unsqueeze(1).float().to(self.device))
            auc_roc_train = roc_auc_score(self.labels.cpu().numpy()[self.train_idx], output.detach().cpu().numpy()[self.train_idx])
            loss_train.backward()
            self.optimizer.step()

#           Edit the training graph for the first numEdit steps
#           Save the original graph as basis
            self.model.eval()
            top_fair_score = fair_metric(preds[self.train_idx],self.labels[self.train].unsqueeze(1).float().to(self.device))
            output = self.model(self.features,self.edge_index.to(self.device))
            preds = (output.squeeze()>0).type_as(self.labels)
            counter_output = self.model(self.counter_features.to(self.device),self.edge_index.to(self.device))
            counter_preds = (counter_output.squeeze()>0).type_as(self.labels)
            top_fair_score = 1 - (preds.eq(counter_preds)[self.train_idx].sum().item()/self.train_idx.shape[0])
            top_edit = self.features.clone()
#           Find the best edit
            if (epoch < self.numEdit):
                for i in range(self.numNode):
                    if i not in self.train_idx:
                        continue
                    for j in range(i,self.numNode):
                        if j not in self.train_idx:
                            continue
                        # Sample every possible one-step edit, calc the counterfactuial fairness, record the best one
                        newGraph = flipAdj(self.edge_index,i,j,self.numNode)
                        t_output = self.model(self.features,newGraph.to(self.device))
                        t_preds = (t_output.squeeze()>0).type_as(self.labels)
                        t_counter_output = self.model(self.counter_features.to(self.device),newGraph.to(self.device))
                        t_counter_preds = (t_counter_output.squeeze()>0).type_as(self.labels)
                        t_fair_score = 1 - (t_preds.eq(t_counter_preds)[self.train_idx].sum().item()/self.train_idx.shape[0])
                        if (t_fair_score > top_fair_score):
                            top_fair_score = t_fair_score
                            top_edit = newGraph
                # Then replace the original with this edit
                #   notice that we only do edit on train_idx, therefore having no effect on val_idx
                self.features = top_edit

#           Evaluate validation set performance separately,
            output = self.model(self.features, self.edge_index)
             # Binary Cross-Entropy
            preds = (output.squeeze()>0).type_as(self.labels)
            loss_val = F.binary_cross_entropy_with_logits(output[self.val_idx ], self.labels[self.val_idx ].unsqueeze(1).float().to(self.device))

            auc_roc_val = roc_auc_score(self.labels.cpu().numpy()[self.val_idx ], output.detach().cpu().numpy()[self.val_idx ])
            f1_val = f1_score(self.labels[self.val_idx ].cpu().numpy(), preds[self.val_idx ].cpu().numpy())
            counter_output = self.model(self.counter_features.to(self.device),self.edge_index.to(self.device))
            counter_preds = (counter_output.squeeze()>0).type_as(self.labels)
            fair_score = 1 - (preds.eq(counter_preds)[self.val_idx].sum().item()/self.train_idx.shape[0])


#           Record the best model 
            if loss_val.item() < best_loss:
                best_loss = loss_val.item()
                torch.save(self.model.state_dict(), 'results/weights/{0}_{1}_{2}.pt'.format(self.model_name, 'bruteforce', self.dataset))

