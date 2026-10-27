#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit synthetic API objects, never a substitute for actual native API evidence."""
import types
import mainchip_two_signal_geometry as g

def fixture():
    class Layer:
        def __init__(self,name,number,level):self.name=name;self.number=number;self.level=level
        def getName(self):return self.name
        def getWidth(self):return 400
        def getWrongWayWidth(self):return 600
        def getDirection(self):return 'HORIZONTAL'
        def getNumber(self):return self.number
        def getRoutingLevel(self):return self.level
    lower=Layer('Metal5',7,5);upper=Layer('Metal6',9,6);cut=Layer('Via5',8,0)
    class Box:
        def __init__(self,layer=lower,values=(1,2,3,4)):self.layer=layer;self.values=values
        def xMin(self):return self.values[0]
        def yMin(self):return self.values[1]
        def xMax(self):return self.values[2]
        def yMax(self):return self.values[3]
        def getTechLayer(self):return self.layer
        def isVia(self):return False
    class Via:
        def getName(self):return 'V56'
        def getTopLayer(self):return upper
        def getBottomLayer(self):return lower
        def getBBox(self):return Box()
        def getBoxes(self):return [Box(lower),Box(cut),Box(upper),Box(upper)]
    via=Via()
    class Master:
        def getName(self):return 'explicit_master'
        def getLib(self):return types.SimpleNamespace(getName=lambda:'explicit_lib')
        def getObstructions(self,include):assert include is True;return [Box()]
    master=Master()
    class Instance:
        def __init__(self,index):self.index=index
        def getName(self):return f'i{self.index:06}'
        def getMaster(self):return master
        def getOrigin(self):return [self.index,0]
        def getOrient(self):return 'R0'
    instances=[Instance(i)for i in range(153130)]
    class Wire:
        def __init__(self):self.raw=[[96,73],[3,52],[4,0],[5,0],[9,11],[10,12],[136,44],[4,20]]
        def length(self):return len(self.raw)
        def getOpcode(self,i):return self.raw[i][0]
        def getData(self,i):return self.raw[i][1]
    wire=Wire()
    class SBox(Box):
        def isVia(self):return True
        def getTechVia(self):return via
        def getBlockVia(self):return None
        def getViaXY(self):return [20,30]
    swire=types.SimpleNamespace(getWireType=lambda:'ROUTED',getWires=lambda:[Box(),SBox()])
    class Net:
        def __init__(self,name):self.name=name;self.iterms=[];self.bterms=[]
        def getName(self):return self.name
        def getSigType(self):return 'CLOCK'if self.name==g.CLOCK else'SIGNAL'
        def isSpecial(self):return False
        def getWire(self):return wire if self.name==g.CLOCK else None
        def getITerms(self):return self.iterms
        def getBTerms(self):return self.bterms
        def getSWires(self):return [swire]if self.name==g.CLOCK else[]
    nets=[Net(name)for name in [g.CLOCK,*g.TARGETS,*[f'n{i:06}'for i in range(143817)]]]
    class ITerm:
        def __init__(self,owner,name='A'):self.owner=owner;self.name=name
        def getNet(self):return self.owner
        def getInst(self):return instances[0]
        def getMTerm(self):return types.SimpleNamespace(getName=lambda:self.name)
        def getGeometries(self):return [(lower,Box())]
    class BTerm:
        def __init__(self,owner,name):self.owner=owner;self.name=name
        def getName(self):return self.name
        def getNet(self):return self.owner
        def getBPins(self):return [types.SimpleNamespace(getPlacementStatus=lambda:'PLACED',getBoxes=lambda:[Box(),Box()])]
    it=ITerm(nets[0]);bt=BTerm(nets[0],'connected_port')
    nets[0].iterms=[it];nets[0].bterms=[bt]
    class Block:
        def getChildren(self):return []
        def getDbUnitsPerMicron(self):return 2000
        def getNets(self):return nets
        def getInsts(self):return instances
        def getITerms(self):return [it,ITerm(None,'DISCONNECTED')]
        def getBTerms(self):return [bt,BTerm(None,'disconnected_port')]
        def getFills(self):return [types.SimpleNamespace(getTechLayer=lambda:lower,getRect=lambda:Box(),
            maskNumber=lambda:0,needsOPC=lambda:False)]
        def getObstructions(self):return [types.SimpleNamespace(getBBox=lambda:Box())]
    block=Block();tech=types.SimpleNamespace(getDbUnitsPerMicron=lambda:2000,getLayers=lambda:[lower,upper,cut])
    db=types.SimpleNamespace(getTech=lambda:tech)
    def get_layer(scope,oid):
        assert scope is tech
        return {73:lower,82:upper,91:cut}.get(oid)
    def get_rule(scope,oid):
        assert scope is tech and oid==52
        return types.SimpleNamespace(getWidth=lambda:800)
    def get_via(scope,oid):
        assert scope is tech and oid==44
        return via
    def get_iterm(scope,oid):
        assert scope is block and oid==11
        return it
    def get_bterm(scope,oid):
        assert scope is block and oid==12
        return bt
    odb=types.SimpleNamespace(dbTechLayer=types.SimpleNamespace(getTechLayer=get_layer),
        dbTechLayerRule=types.SimpleNamespace(getTechLayerRule=get_rule),
        dbTechVia=types.SimpleNamespace(getTechVia=get_via),
        dbVia=types.SimpleNamespace(getVia=lambda scope,oid:None),
        dbITerm=types.SimpleNamespace(getITerm=get_iterm),dbBTerm=types.SimpleNamespace(getBTerm=get_bterm))
    return types.SimpleNamespace(odb=odb,db=db,block=block,tech=tech,lower=lower,upper=upper,cut=cut,
        wire=wire,nets=nets,instances=instances,master=master,it=it,bt=bt,ITerm=ITerm,BTerm=BTerm,Layer=Layer)
