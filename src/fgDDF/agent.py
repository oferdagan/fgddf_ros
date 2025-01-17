
"""
agent class for multi-agent decentralized inference
agent is the base class for all agents in the network

"""
# sys.path.append(r"D:\Studies\Research\Code\pythonCode\fglib")
from fglib import graphs , nodes, inference, rv, utils
from fusionAlgo import *
import networkx as nx
import matplotlib.pyplot as plt
# from copy import deepcopy
from factor_utils import *

class agent(object):

    """docstring for agent class.
        input:
        varSet - set of variables in agent i inference task
        priors - a dictionary containing prior definitions for each variable in varSet

    """

    def __init__(self, varSet, dynamicList, filter, fusionAlgorithm, condVar = None , variables = None ):
        self.fg = graphs.FactorGraph()
        self.varSet = varSet
        self.factorCounter = 0
        self.filter = filter
        self.id = id(self)
        self.dynamicList = dynamicList
        self.fusionAlgorithm = fusionAlgorithm
        self.varList = dict()
        self.fusion = globals()[fusionAlgorithm](fusionAlgorithm)
        self.condVar = condVar   # need to be automated later
       # self.x_hat = dict()

        for var in varSet:
            if var in dynamicList:
                """need to set the instances to be automatic and correct"""
                x = nodes.VNode(var+"_0", rv.Gaussian.inf_form(None, None))
                self.varList[var] = x
                setattr(self, var+"_Current",  var+"_0")
            else:
                """need to set the instances to be automatic and correct"""
                x = nodes.VNode(var, rv.Gaussian)
                self.varList[var] = x
                setattr(self, var+"_Current",  var)


            self.fg.set_node(x)
            self.fg.nodes[x]['comOrLoc']=variables[var]['Type']


    def set_prior(self, prior):
        """ add prior factor to the graph

            input:
                varNode - the variable node that the prior factor is defined on
                prior - a dictionary containing definitions for the prior factor,
                        currently only infMAt and infVec for a information form Gaussian pdf
                        and: inst - Instances of the class VNode representing the variables of
                        the mean vector and covariance matrix, respectively. The number
                        of the positional arguments must match the number of dimensions
                        of the Numpy arrays.

            for now the factors are defined as Gaussian in information form

        """
        self.prior = prior
        list_vnodes = self.fg.get_vnodes()
        varNode = []
        for i in range(len(list_vnodes)):
            if str(list_vnodes[i]) in prior:
                 varNode = list_vnodes[i]

            instances = []
            try:
                for j in range(prior[str(list_vnodes[i])]['dim']):
                    instances.append(varNode)


                f = nodes.FNode('f_'+str(self.factorCounter), rv.Gaussian.inf_form(prior[str(list_vnodes[i])]['infMat'],
                    prior[str(list_vnodes[i])]['infVec'], *instances))
                self.factorCounter = self.factorCounter+1
                self.fg.set_node(f)
                self.fg.set_edge(varNode, f)
            except:
                print('No prior defined for variable ', str(list_vnodes[i]))

    def set_fusion(self, agent_j, variables):
        self.fusion.set_channel(self, agent_j)

        if 'CF' in self.fusionAlgorithm:
            commonVars = self.fusion.commonVars[agent_j.id]
            dynamicList = self.dynamicList & commonVars
            self.fusion.fusionLib[agent_j.id] = agent(commonVars, dynamicList, self.filter, self.fusionAlgorithm, None, variables )
            self.fusion.fusionLib[agent_j.id].set_prior(self.prior)
        elif 'CI' in self.fusionAlgorithm:
            commonVars = self.fusion.commonVars[agent_j.id]
            dynamicList = self.dynamicList & commonVars
            self.fusion.fusionLib[agent_j.id] = agent(commonVars, dynamicList, self.filter, self.fusionAlgorithm, None, variables )


    def sendMsg(self, agents, agent_i, agent_j):
        """
            returns a dictionary of with keys: dims, infMat, infVec
            dims is a list of names of variables
        """
        commonVars = self.fusion.commonVars[agents[agent_j]['agent'].id]
        msg = self.fusion.prepare_msg(agents[agent_i]['agent'], agents[agent_i]['filter'], commonVars, agents[agent_j]['agent'].id)

        return msg


    def fuseMsg(self):
        self.fusion.fuse(self)



    def build_semiclique_tree(self):
        """
        This function takes a factor graph and returns an additional factor graph that contains
        the minimum cliques that will keep the graph without cycles so the sum product algorithm can
        run on it.

        cliqueFlag - if 0: no cliques, graph is identical to the agents' graph (with no loops)
                     if 1: there are cliques and new factors need to be built
        """
        self.clique_fg = graphs.FactorGraph()
        self.clique_fg.graph['cliqueFlag'] = 0
        Vars = deepcopy(self.varSet)
        cliques = dict()
        separator =set()
        commonVars = []
        i = 0
        # j = 1
        s = set()

        sets = list(self.fusion.commonVars.values())
        separator = set.intersection(*sets)

        # Initialize an empty set for the intersection of other sets


        intersection_other = set()
        # Calculate the intersection of other sets
        if len(sets)>2:
            for k in range(len(sets)):
                other_sets = [s for j, s in enumerate(sets) if j != k]
                intersection = set.intersection(*other_sets)
                intersection_other.update(intersection)

        # Calculate the variables that are in the intersection of other sets but not all sets
            intersection_other.difference_update(separator)
        if len(intersection_other)>0:
            cliques[i] = intersection_other
            i+=1
        # Calculate the variables that are not in any intersection
        not_in_any_intersection = set.union(*sets) - set.union(separator, intersection_other)

        for v in not_in_any_intersection:
            cliques[i] = {v}
            i+=1
    # 1. reason about cliques:
    #     for key in self.fusion.commonVars:
    #
    #         [commonVars.append(c) for c in self.fusion.commonVars[key]]   # this line is not used anywhere else
    #         if len(self.fusion.commonVars[key])>1:
    #             for k in cliques:
    #                 if cliques[k] & self.fusion.commonVars[key]:
    #                     tmp = (list(cliques[k] & self.fusion.commonVars[key]))
    #                     for n in tmp:
    #                         separator.add(n)
    #                     [cliques[k].remove(s) for s in separator if s in cliques[k]]
    #
    #             cliques[i] = self.fusion.commonVars[key]-separator
    #             [Vars.remove(v) for v in cliques[i] if v in Vars]
    #             i+=1


        # need to check independence
        # if len(set(commonVars)-self.condVar)==0:  # for centralized and special cases.
        #     separationClique = self.condVar
        #     cliques = dict()
        #     i = 1
        # else:
        separationClique = self.condVar | separator   # union
        [Vars.remove(v) for v in separationClique if v in Vars]

        #TODO check, and add local variables to clique
        separationClique = separationClique | Vars
        [Vars.remove(v) for v in separationClique if v in Vars]

        if len(cliques)==1 and len(cliques[0]-set(commonVars))==0 and len(Vars)==0:
            return


        vnodes = self.fg.get_vnodes( )
        # find and change the dynamic variable name in cliques:
        nodesToRemove = []
        for n in range(0, i):
            varName = []
            for var in cliques[n]:
                for v in vnodes:
                    if str(v).find(var) != -1:
                        varName.append(str(v))
                        nodesToRemove.append(v)
                        break
            cliques[n] = set(varName)

        for v in nodesToRemove:
            print(str(v))
            vnodes.remove(v)
        # find and change the dynamic variable name in Vars:
        nodesToRemove=[]
        varName = []
        for var in Vars:
            for v in vnodes:
                if str(v).find(var) != -1:
                    varName.append(str(v))
                    nodesToRemove.append(v)
                    break
        Vars = set(varName)

        try:
            for v in nodesToRemove:
                vnodes.remove(v)
        except:
            1

        # find and change the dynamic variable name in separationClique:

        varName=[]
        for var in separationClique:
            for v in vnodes:
                if str(v).find(var) != -1:
                    varName.append(str(v))
                    break
        separationClique=set(varName)

        # 2. add nodes to graph
        c_counter = 1
        self.clique_fg.graph['unaryVars'] = []
        self.clique_fg.graph['Cliques'] = []
        for v in Vars:
            x = nodes.VNode(v, rv.Gaussian)
            self.clique_fg.set_node(x)
            self.clique_fg.nodes[x]['vars'] = {v}
            self.clique_fg.graph['unaryVars'].append(v)

        # remove empty cliques
        tmpCliques = {key: cliques[key] for key in cliques if cliques[key] != s}
        cliques = tmpCliques
        for key, value in cliques.items():
            self.clique_fg.graph['cliqueFlag'] = 1
            x = nodes.VNode('C'+str(c_counter), rv.Gaussian)

            self.clique_fg.set_node(x)
            self.clique_fg.nodes[x]['vars'] = value
            self.clique_fg.graph['Cliques'].append('C'+str(c_counter))
            c_counter+=1

        if len(separationClique)==1:
            x = nodes.VNode('Sep', rv.Gaussian)
            self.clique_fg.set_node(x)
            self.clique_fg.nodes[x]['vars'] = separationClique
        elif len(separationClique)>1:
            x = nodes.VNode('Sep', rv.Gaussian)
            self.clique_fg.set_node(x)
            self.clique_fg.nodes[x]['vars'] = separationClique
            self.clique_fg.graph['cliqueFlag'] = 1

        self.clique_fg.graph['separationClique'] = separationClique
        return

    def add_factors_to_clique_fg(self):
        """
        This function builds and adds factors to the semiclique_tree factor graph

        """
        # if the graph has no cliques, its structure is identical to the original graph
        if self.clique_fg.graph['cliqueFlag']==0:
            # tmpCliqueGraph  = deepcopy(self.fg)
            return self.fg

        # else - need to build factors
        tmpCliqueGraph = deepcopy(self.clique_fg)
        tmpMainFg = deepcopy(self.fg)
        # tmpMainFg = self.fg

        factorCounter = 1
        fList = []
        cFactor = []
        # vnodes=tmpMainFg.get_vnodes()
        factorFlag = []
        s = findVNode(tmpCliqueGraph, 'Sep')
        # add factors between cliques and separator
        for cName in tmpCliqueGraph.graph['Cliques']:
            c = findVNode(tmpCliqueGraph, cName)
            i = 1
            # loop over all variables in the clique
            for n in tmpCliqueGraph.nodes[c]['vars']:
                # find node in agents' fg:
                factorFlag = False
                # summarize all factors connected to nodes in agents' fg
                for f in list(tmpMainFg[findVNode(tmpMainFg, n)]):
                    if f not in fList:
                        factorFlag = True
                        if i==1:
                            cFactor = f
                            i = 0
                        else:
                            cFactor.factor = cFactor.factor.__mul__(f.factor)
                        fList.append(f)

            instances = []
            instances0 = []
            tmpCliqueGraph.nodes[c]['dims'] = []
            for d in cFactor.factor.dim:
                if str(d) in tmpCliqueGraph.nodes[c]['vars']:
                    instances.append(c)
                    instances0.append(c)
                    tmpCliqueGraph.nodes[c]['dims'].append(str(d))  # save dims:
                else:
                    instances.append(s)
            if factorFlag:
                # add factor connecting all variables in vars:
                f_i = nodes.FNode("f_"+str(factorCounter),
                        rv.Gaussian.inf_form(cFactor.factor._W, cFactor.factor._Wm, *instances))
                # set dims correctly:

                tmpCliqueGraph.set_node(f_i)
                factorCounter+=1

                tmpCliqueGraph.set_edge(c, f_i)
                if s in instances:
                    tmpCliqueGraph.set_edge(s, f_i)

            f_j = nodes.FNode("f_100"+str(factorCounter),
                    rv.Gaussian.inf_form(np.zeros((len(instances0),len(instances0))), np.zeros((len(instances0),1)), *instances0))
            tmpCliqueGraph.set_node(f_j)
            tmpCliqueGraph.set_edge(c, f_j)

        i = 1
        sFactor =[]
        # loop over all variables in the clique
        for n in tmpCliqueGraph.nodes[s]['vars']:
            # summarize all factors connected to nodes in agents' fg
            for f in list(tmpMainFg[findVNode(tmpMainFg, n)]):
                memberFlag = 1
                for j in tmpMainFg[f]:
                    if str(j) not in tmpCliqueGraph.nodes[s]['vars']:
                        memberFlag = 0
                        break

                if f not in fList and memberFlag ==1:
                    if i==1:
                        sFactor = f
                        i = 0
                    else:
                        sFactor.factor = sFactor.factor.__mul__(f.factor)
                    fList.append(f)

        instances = []
        tmpCliqueGraph.nodes[s]['dims'] = []
        for d in sFactor.factor.dim:
            instances.append(s)
            tmpCliqueGraph.nodes[s]['dims'].append(str(d))   # save dims:


        # add factor connecting all variables in vars:
        f_i = nodes.FNode("f_"+str(factorCounter),
                rv.Gaussian.inf_form(sFactor.factor._W, sFactor.factor._Wm, *instances))

        tmpCliqueGraph.set_node(f_i)
        factorCounter+=1

        tmpCliqueGraph.set_edge(s, f_i)

        f_j = nodes.FNode("f_1000"+str(factorCounter),
                rv.Gaussian.inf_form(np.zeros((len(instances),len(instances))), np.zeros((len(instances),1)), *instances))
        tmpCliqueGraph.set_node(f_j)
        tmpCliqueGraph.set_edge(s, f_j)

        # add factors of unary variables:
        for uName in tmpCliqueGraph.graph['unaryVars']:
            u = findVNode(tmpCliqueGraph, uName)
            i = 1
            # loop over all variables in the clique
            for n in tmpCliqueGraph.nodes[u]['vars']:
                factorFlag = False

                # find node in agents' fg:
                uFactor =[]
                # summarize all factors connected to nodes in agents' fg
                for f in list(tmpMainFg[findVNode(tmpMainFg, n)]):

                    if f not in fList:
                        factorFlag = True
                        if i==1:
                            uFactor = f
                            i = 0
                        else:
                            uFactor.factor = uFactor.factor.__mul__(f.factor)
                        fList.append(f)

                if factorFlag:
                    instances = []
                    instances0 = []
                    for d in uFactor.factor.dim:
                        if str(d) in tmpCliqueGraph.nodes[u]['vars']:
                            instances.append(u)
                            instances0.append(u)
                        else:
                            instances.append(s)

                # add factor connecting all variables in vars:
                    f_i = nodes.FNode("f_"+str(factorCounter),
                            rv.Gaussian.inf_form(uFactor.factor._W, uFactor.factor._Wm, *instances))

                    tmpCliqueGraph.set_node(f_i)
                    factorCounter+=1

                    tmpCliqueGraph.set_edge(u, f_i)

                    if s in instances:
                        tmpCliqueGraph.set_edge(s, f_i)

                    f_j = nodes.FNode("f_10000"+str(factorCounter),
                            rv.Gaussian.inf_form(np.zeros((len(instances0),len(instances0))), np.zeros((len(instances0),1)), *instances0))
                    tmpCliqueGraph.set_node(f_j)
                    tmpCliqueGraph.set_edge(u, f_j)

        return tmpCliqueGraph
