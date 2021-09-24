from spydrnet.ir.first_class_element import FirstClassElement
from spydrnet.ir.port import Port
from spydrnet.ir.cable import Cable
from spydrnet.ir.instance import Instance
from spydrnet.ir.outerpin import OuterPin
from spydrnet.ir.views.listview import ListView
from spydrnet.ir.views.setview import SetView
from spydrnet.global_state import global_callback
from itertools import combinations
from spydrnet.global_state.global_callback import _call_create_definition
from copy import deepcopy, copy, error


class Definition(FirstClassElement):
    """
    Represents a definition of a cell, module, entity/architecture, or paralleled structure object.

    Contains a pointer to parent library, ports, cables, and instances.
    """
    __slots__ = ['_library', '_ports', '_cables', '_children', '_references']

    def __init__(self, name=None, properties=None):
        """Creates an empty object of type definition

        parameters
        ----------

        name - (str) the name of this instance
        properties - (dict) the dictionary which holds the properties
        """
        super().__init__()
        self._library = None
        self._ports = list()
        self._cables = list()
        self._children = list()
        self._references = set()
        _call_create_definition(self)

        if name != None:
            self.name = name

        if properties != None:
            assert isinstance(
                properties, dict), "properties must be a dictionary"
            for key in properties:
                self[key] = properties[key]

    @property
    def library(self):
        """
        Get the library that contains this definition
        """
        return self._library

    @property
    def ports(self):
        """
        Get the ports that are instanced in this definition
        """
        return ListView(self._ports)

    @ports.setter
    def ports(self, value):
        """Reorder ports that are instanced in this definition.

        Use remove_port and add_port to remove and add ports
        respectively

        parameters
        ----------

        value - (List of type Port objects) the reordered list of ports
        """
        target = list(value)
        target_set = set(target)
        assert len(target) == len(target_set) and set(self._ports) == target_set, \
            "Set of values do not match, this function can only reorder values, values must be unique"
        self._ports = target

    @property
    def cables(self):
        """
        Get the cables that are instanced in this definition.
        """
        return ListView(self._cables)

    @cables.setter
    def cables(self, value):
        """
        Reorder the cables in this definition. Use add_cable and remove_cable to add or remove cables.


        parameters
        ----------

        value - (List of type Cable objects) the reordered list of cables
        """
        target = list(value)
        target_set = set(target)
        assert len(target) == len(target_set) and set(self._cables) == set(target), \
            "Set of values do not match, this function can only reorder values, values must be unique"
        self._cables = target

    @property
    def children(self):
        """
        Return a list of all instances instantiated in this definition
        """
        return ListView(self._children)

    @children.setter
    def children(self, value):
        """
        Reorder the list of instances instantiated in this definition use add_child and remove_child to add or remove
        instances to or from the definition

        parameters
        ----------

        value - (List of type Instance objects) the reordered list of instances
        """
        target = list(value)
        target_set = set(target)
        assert len(target) == len(target_set) and set(self._children) == target_set, \
            "Set of values do not match, this function can only reorder values, values must be unique"
        self._children = target

    @property
    def references(self):
        """
        Get a list of all the instances of this definition
        """
        return SetView(self._references)

    def is_leaf(self):
        """
        Check to see if this definition represents a leaf cell.

        Leaf cells are cells with no children instances or no
        children cables. Blackbox cells are considered leaf cells as well as direct pass through cells with cables only
        """
        if len(self._children) > 0 or len(self._cables) > 0:
            return False
        return True

    def create_port(self, name=None, properties=None, is_downto=None, is_scalar=None, lower_index=None, direction=None):
        """Create a port, add it to the definition, and return that port.

        parameters
        ----------

        name - (str) the name of this instance
        properties - (dict) the dictionary which holds the properties
        id_downto - (bool) set the downto status. Downto is False if the right index is higher than the left one, True otherwise
        is_scalar - (bool) set the scalar status. Return True if the item is a scalar False otherwise.
        lower_index - (int) get the value of the lower index of the array.
        direction - (Enum) Define the possible directions for a given port. (UNDEFINED, INOUT, IN, OUT)

        """
        port = Port(name, properties, is_downto,
                    is_scalar, lower_index, direction)
        self.add_port(port)
        return port

    def add_port(self, port, position=None):
        """Add a preexisting port to the definition.

        This port must not be a member of any definition

        parameters
        ----------

        port - (Port) the port to add to the definition

        position - (int, default None) the index in the port list at which to add the port
        """
        assert port.definition is not self, "Port already included in definition"
        assert port.definition is None, "Port already belongs to a different definition"
        global_callback._call_definition_add_port(self, port)
        if position is not None:
            self._ports.insert(position, port)
        else:
            self._ports.append(port)
        port._definition = self
        for reference in self.references:
            for pin in port.pins:
                reference._pins[pin] = OuterPin(reference, pin)

    def remove_port(self, port):
        """Remove a port from the definition.

        his port must be a member of the definition in order to be removed

        parameters
        ----------

        port - (Port) the port to be removed
        """
        assert port.definition == self, "Port is not included in definition"
        self._remove_port(port)
        self._ports.remove(port)

    def remove_ports_from(self, ports):
        """Remove a set of ports from the definition.

        All these ports must be included in the definition

        parameters
        ----------

        ports - (Set containing Port type objects) the ports to remove from the definition
        """
        if isinstance(ports, set):
            excluded_ports = ports
        else:
            excluded_ports = set(ports)
        assert all(x.definition == self for x in excluded_ports), "Some ports to remove are not included in the " \
                                                                  "definition."
        for port in excluded_ports:
            self._remove_port(port)
        self._ports = list(x for x in self._ports if x not in excluded_ports)

    def _remove_port(self, port):
        """Internal function to dissociate the port from the definition

        Parameters
        ----------

        port - (Port) the port to remove from the definition
        """
        global_callback._call_definition_remove_port(self, port)
        for reference in self.references:
            for pin in port.pins:
                outer_pin = reference.pins[pin]
                wire = outer_pin.wire
                if wire:
                    wire.disconnect_pin(outer_pin)
                del reference._pins[pin]
                outer_pin._instance = None
                outer_pin._inner_pin = None
        port._definition = None

    def create_child(self, name=None, properties=None, reference=None):
        """Create an instance to add to the definition, add it, and return the instance.

        This functions calls the add_child funciton.

        parameters
        ----------

        name - (str) the name of this instance
        properties - (dict) the dictionary which holds the properties

        Example
        -------

        To create a child:

        >>> definition = sdn.Definition()
        >>> child_instance = definition.create_child()
        >>> child_instance.name = "child_instance"
        >>> child_instance.reference = reference_definition

        To create a child with optional parameters

        >>> child_instance = definition.create_child(name="child_instance", reference=reference_definition)

        The reference of the instance is the definition that initialized this instance.
        """
        instance = Instance(name, properties)
        instance.reference = reference
        self.add_child(instance)
        return instance

    def add_child(self, instance, position=None):
        """Add an existing instance to the definition.

        This instance must not already be included in a definition.
        It add the instance as a child into the given position.
        Append to the end of the list if no position is given.
        It will set the parent of the instance to this definition.

        parameters
        ----------

        instance - (Instance) the instance to add as a child of the definition

        position - (int, default None) the index in the children list at which to add the instance.
        """
        assert instance.parent is not self, "Instance already included in definition"
        assert instance.parent is None, "Instance already belongs to a different definition"
        global_callback._call_definition_add_child(self, instance)
        if position is not None:
            self._children.insert(position, instance)
        else:
            self._children.append(instance)
        instance._parent = self

    def remove_child(self, child):
        """Remove an instance from the definition.

        The instance must be a member of the definition already

        parameters
        ----------

        instance - (Instance) the instance to be removed from the definition
        """
        assert child.parent == self, "Instance is not included in definition"
        self._remove_child(child)
        self._children.remove(child)

    def remove_children_from(self, children):
        """Remove a set of instances from the definition.

        All instances must be members of the definition

        parameters
        ----------

        children - (Set of Instance type objects) the children to be removed from the definition
        """
        if isinstance(children, set):
            excluded_children = children
        else:
            excluded_children = set(children)
        assert all(
            x.parent == self for x in excluded_children), "Some children are not parented by the definition"
        included_children = list()
        for child in self._children:
            if child not in excluded_children:
                included_children.append(child)
            else:
                self._remove_child(child)
        self._children = included_children

    def _remove_child(self, child):
        """
        Internal function for dissociating a child instance from the definition.
        """
        global_callback._call_definition_remove_child(self, child)
        child._parent = None

    def create_cable(self, name=None, properties=None, is_downto=None, is_scalar=None, lower_index=None):
        """Create a cable, add it to the definition, and return the cable.

        parameters
        ----------

        name - (str) the name of this instance
        properties - (dict) the dictionary which holds the properties
        id_downto - (bool) set the downto status. Downto is False if the right index is higher than the left one, True otherwise
        is_scalar - (bool) set the scalar status. Return True if the item is a scalar False otherwise.
        lower_index - (int) get the value of the lower index of the array.
        """
        cable = Cable(name, properties, is_downto, is_scalar, lower_index)
        self.add_cable(cable)
        return cable

    def add_cable(self, cable, position=None):
        """Add a cable to the definition.

        The cable must not already be a member of another definition.

        parameters
        ----------

        cable - (Cable) the cable to be added

        position - (int, default None) the position in the cable list at which to add the cable
        """
        assert cable.definition is not self, "Cable already included in definition"
        assert cable.definition is None, "Cable already belongs to a different definition"
        global_callback._call_definition_add_cable(self, cable)
        if position is not None:
            self._cables.insert(position, cable)
        else:
            self._cables.append(cable)
        cable._definition = self

    def remove_cable(self, cable):
        """Remove a cable from the definition.

        The cable must be a member of the definition.

        parameters
        ----------

        cable - (Cable) the cable to be removed from the definition
        """
        assert cable.definition == self, "Cable is not included in definition"
        self._remove_cable(cable)
        self._cables.remove(cable)

    def remove_cables_from(self, cables):
        """Remove a set of cables from the definition.

        The cables must be members of the definition

        parameters
        ----------

        cables - (Set of Cable type objects) the cables to be remove from the definition
        """
        if isinstance(cables, set):
            excluded_cables = cables
        else:
            excluded_cables = set(cables)
        assert all(
            x.definition == self for x in excluded_cables), "Some cables are not included in the definition"
        included_cables = list()
        for cable in self._cables:
            if cable not in excluded_cables:
                included_cables.append(cable)
            else:
                self._remove_cable(cable)
        self._cables = included_cables

    def _remove_cable(self, cable):
        """Dissociate the cable from this definition.

        This function is internal and should not be called.
        """
        global_callback._call_definition_remove_cable(self, cable)
        cable._definition = None

    def merge_multiple_instance(self, instances_list_tuple, new_definition_name=None, pin_map=None):
        """
        This method can merge multiple group of instances having same reference.
        First pair of the instances_list_tuple is used to create new definition
        and this def is reuse while grouping remaining group of instances
        instances_list_tuple = [(inst_1, inst_2, ...., inst_n), <instance_name>]
        new_definition_name = Name for the new definition
        pin_map             = Function of dictionary to rename pins
        """
        mainDef = None
        instance_list = []
        for instances_list, instance_name in instances_list_tuple:
            newDef, newInst, _ = self.merge_instance(instances_list,
                                new_definition_name=f"{new_definition_name}_{instance_name}",
                                new_instance_name=instance_name,
                                pin_map=pin_map)
            instance_list.append(newInst)
            if not mainDef:
                mainDef = newDef
                mainDef.name = new_definition_name
            else:
                newInst.reference = mainDef
                self.library.remove_definition(newDef)
        return mainDef, instance_list


    def merge_instance(self, instances_list, new_definition_name=None, new_instance_name=None, pin_map=None):
        """
        instances_list      : List of instances to be merged
        new_definition_name : Name of the new definition created
        new_instance_name   : Name of the new instance created
        pin_map : function or a dictionary mapping pin of each module
                  function call arguments:
                  get_pin_name(<definition_name:<str>, <pin_name:<str>,
                                <instance_name:<str>)
        """
        RenameMap = {} # Stores the final rename map

        # ====== Input Sanity checks
        for eachModule in instances_list:
            assert isinstance(eachModule, Instance), "Modulelist contains none non-intance object"

        if pin_map:
            if isinstance(pin_map,dict):
                pin_map_copy = pin_map
                pin_map = lambda x, y, _: pin_map_copy.get(x,{}).get(y,{})
            if not callable(pin_map):
                print("pin_map argument should be dictionary or function, received {type(pin_map)}" )

        # ====== Create a new definition
        if not new_definition_name:
            new_def_name = "_".join([each.reference.name for each in instances_list]) + "_merged"
            print(f"Inferred definition name {new_def_name} ")
        else:
            new_def_name = new_definition_name
        newMod = self.library.create_definition(name=new_def_name)

        # ===== Create instance of the definition
        if not new_instance_name:
            new_instance_name = f"{new_def_name}_1"
        MergedModule = self.create_child( name=new_instance_name,
                        reference=newMod)

        # ===== Interate over each module and create new module
        for index, eachM in enumerate(instances_list):
            print(f"******************************************************")
            print(f"Iterating {eachM.name} [{eachM.reference.name}]")
            print(f"******************************************************")

            RenameMap[eachM.reference.name]= {}
            RenameMap[eachM.reference.name][index] = {}
            currMap = RenameMap[eachM.reference.name][index]
            IntInst = newMod.create_child(name=eachM.name,
                                        reference=eachM.reference)
            # Iterate over each port of current instance
            for p in eachM.get_ports():
                pClone = p.clone() # It copied all pins, wires and cables

                for eachSuffix in [""]+[f"_{i}" for i in range(10)]:
                    newName = pClone.name + eachSuffix
                    if not len(list(newMod.get_ports(newName))):
                        break
                newCable = newMod.create_cable(
                                name = newName,
                                is_downto = pClone.is_downto,
                                is_scalar = pClone.is_scalar,
                                lower_index = pClone.lower_index,
                            )

                # Create connection inside new definition
                for eachPClone, eachP in zip(pClone.pins, p.pins):
                    w = newCable.create_wire()
                    w.connect_pin(eachPClone)
                    w.connect_pin(IntInst.pins[eachP])
                pClone.change_name(newName)
                newMod.add_port(pClone)

                currMap[p.name] = newName


                for eachPin in p.pins:
                    instOutPin = eachM.pins[eachPin]
                    conWire = instOutPin.wire
                    instPin = MergedModule.pins[pClone.pins[eachPin.index()]]
                    conWire.connect_pin(instPin)
                    instOutPin.wire.disconnect_pin(instOutPin)
                    newCable.wires[eachPin.index()].connect_pin(instOutPin)

            self.remove_child(eachM)
        return newMod, MergedModule, RenameMap

    def OptPins( self, pins=lambda x: True, dryrun=False, merge=True, absorb=True):
        """
        This method optimizes the definitions pins
        dryrun : Just performs the dryrun and list the pins which can be
                  merged or absorbed
        pins : only consider specific pins, provide filter function
        absorb : if two pins are only connected to each other they
                    will be absorbed and internal connection will be made
        merge : if two pins are connected to each other and few other
                    instances, one of the pin will be absorbed and other
                    will exist
        """
        duplicatePins = [] # Set of all pins which can be merged or absorbed
        absorbPins = [] # Subset of duplicate pins
        defPort = list([x for x in self.get_ports() if pins(x.name)])

        # Iterate over all the ports pairs of the definition
        for fromPort, toPort in combinations(defPort, 2):
            if len(fromPort.pins) == len(toPort.pins):
                # Compare only when port has same width
                sameNet = True
                singleWire = True
                for eachPin1, eachPin2 in zip(fromPort.pins,toPort.pins):
                    for eachInst in self.references:
                        eachPin1 = eachInst.pins[eachPin1]
                        eachPin2 = eachInst.pins[eachPin2]
                        if not eachPin1.wire == eachPin2.wire:
                            sameNet = False
                            break
                        elif singleWire:
                            singleWire = set(eachPin1.wire.pins) == set((eachPin1, eachPin2))

                if sameNet:
                    # Check if frompin exist in the previous pairs
                    alreadyPaired = next((dupliPins for dupliPins in duplicatePins if fromPort in dupliPins), None)
                    if alreadyPaired:
                        if not toPort in alreadyPaired:
                            alreadyPaired.append(toPort)
                    else:
                        portPair = [fromPort, toPort]
                        duplicatePins.append(portPair)
                    if singleWire:
                        absorbPins.append(portPair)


        if not dryrun:
            for ports in duplicatePins:
                print(f"[info] Merged Ports{[port.name for port in ports]}")

                for eachP1Pin in ports[0].pins:
                    ww = eachP1Pin.wire
                    for eachPort in ports[1:]:
                        # Remove all internal connection
                        wwP2= eachPort.pins[eachP1Pin.index()].wire
                        for eachPin in wwP2.pins:
                            if isinstance(eachPin, OuterPin):
                                # Selects pins connected to the instance
                                eachPin.wire.disconnect_pin(eachPin)
                                ww.connect_pin(eachPin)

                for eachPort in ports[1:]:
                    self.remove_cable(eachPort.pins[0].wire.cable)
                    self.remove_port(eachPort)
                if ports in absorbPins:
                    self.remove_cable(ports[0].pins[0].wire.cable)
                    self.remove_port(ports[0])

        return duplicatePins if merge else absorbPins if absorb else None


    def _clone_rip_and_replace(self, memo):
        """If an instance that is a reference of this definition was cloned then update the list of references of the definition.

        For each of the children instances, we should also update the reference to refer to any cloned dictionaries
        inner pins now also need to be updated with new inner pins for each of the definitions that was cloned."""
        new_references = set()
        for instance in self._references:
            # if the instance was cloned then replace it in our references also update its reference
            if instance in memo:
                new_instance = memo[instance]
                new_references.add(new_instance)
            else:
                new_references.add(instance)
        self._references = new_references

        for instance in self._children:
            if instance.reference in memo:
                instance._reference = memo[instance.reference]
                instance._clone_rip_and_replace_in_library(memo)

    def _clone_rip(self):
        """Remove from its current environmnet.

        add all instances to their appropriate reference lists.
        """
        for instance in self._children:
            instance._reference._references.add(instance)
        self._references = set()

    def _clone(self, memo):
        """Not api safe clone function

        clone leaving all references in tact.
        the element can then either be ripped or ripped and replaced"""
        assert self not in memo, "the object should not have been copied twice in this pass"
        c = Definition()
        memo[self] = c
        c._data = deepcopy(self._data)
        c._library = None

        new_ports = list()
        for p in self.ports:
            new_ports.append(p._clone(memo))
        c._ports = new_ports

        new_cables = list()
        for ca in self.cables:
            new_cables.append(ca._clone(memo))
        c._cables = new_cables

        new_children = list()
        for ch in self.children:
            new_children.append(ch._clone(memo))
        c._children = new_children

        c._references = copy(self._references)

        for port in c._ports:
            port._definition = c
            port._clone_rip_and_replace(memo)

        for cable in c._cables:
            cable._definition = c
            cable._clone_rip_and_replace(memo)

        for instance in c._children:
            instance._parent = c
            instance._clone_rip_and_replace_in_definition(memo)

        return c

    def clone(self):
        """Clone the definition in an api safe way.


        The cloned object will have the following properties

         * the definition will be orphaned and will not belong to any library
         * each of the sub elements of the definition will also be cloned and the connection structure between them will be updated.
         * the cloned instances will still point to the reference to which the pointed before. They will also be members of the references list of those definitions.

        """
        c = self._clone(dict())
        c._clone_rip()
        return c

    # def __repr__(self):
    #     return "<spydrnet.definition " + str(self.name) + ", cables:"+str(len(self.cables)) + ", children:"+str(len(self.children)) + ", ports:"+str(len(self.ports)) + ", references:"+str(len(self.references)) + ">"

    def __str__(self):
        """Re-define the print function so it is easier to read"""
        rep = super().__str__()
        rep = rep[:-1] + '; '
        if self.library is None:
            rep += 'Library undefined'
        elif self.library.name is None:
            rep += 'Library.name undefined'
        else:
            rep += 'Library.name \'' + self.library.name + '\''
        rep += '; '
        rep += 'ports: '
        rep += str(sum(1 for _ in self.get_ports()))
        rep += '; cables: '
        rep += str(sum(1 for _ in self.get_cables()))
        rep += '; children: '
        rep += str(len(self.children))
        rep += '; references: '
        rep += str(len(self.references))
        rep += '>'
        return rep
