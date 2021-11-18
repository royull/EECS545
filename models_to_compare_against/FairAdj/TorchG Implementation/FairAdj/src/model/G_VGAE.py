import torch
from torch import nn
import torch_geometric.nn as Gnn
import torch_geometric as torchG

class VGAE(nn.Module):
	def __init__(self, input_feat_dim, hidden_dim1, hidden_dim2):
		super(VGAE,self).__init__()
		self.gc1 = Gnn.GCNConv(input_feat_dim,hidden_dim1)
		self.gc_mean = Gnn.GraphConv(hidden_dim1,hidden_dim2)
		self.gc_logvar = Gnn.GraphConv(hidden_dim1,hidden_dim2)
		self.decode = Gnn.InnerProductDecoder()
	
	def encode(self, x, adj):
		tadj = adj
		print(type(adj))
		if (isinstance(adj,torch.sparse_coo_tensor)):
			tadj = adj.to_dense()
		hideen1 = self.gc1(x,adj)
		return self.gc_mean(hideen1,adj), self.gc_logvar(hideen1,adj)

	def reparameterize(self, mu, logvar):
		if (isinstance(adj,torch.sparse_coo_tensor)):
			tadj = adj.to_dense()
		if self.training:
			std = torch.exp(logvar)
			eps = torch.randn_like(std)
			return eps.mul(std).add_(mu)
		else:
			return mu
	
	def forward(self, x, adj):
		mu, logvar = self.encode(x, adj)
		z = self.reparameterize(mu, logvar)
		return self.decode(z), z, mu, logvar
	
	def get_parameters(self):
		return [{"params": self.parameters(), "lr_mult": 1.}]
	