from collections import deque, OrderedDict
from spydrnet.ir import Port
from spydrnet.ir import Cable
import spydrnet.parsers.verilog.verilog_tokens as vt
import spydrnet as sdn


class Composer:

    def __init__(self, definition_list=[], write_blackbox=True, skip_constraints=False, sort_all=False, show_assign_instance_name=False):
        """ Write a verilog netlist from SDN netlist

        parameters
        ----------

        definition_list - (list[str]) list of definitions to write
        write_blackbox - (bool) Skips writing black boxes/verilog primitives
        defparam - (bool) Compose parameters in *defparam* statements instead of using #()
        skip_constraints - (bool) Skips writing constraints to the output verilog file
        reverse - (bool) Compose the netlist bottom to top
        """
        self.file = None
        self.direction_string_map = {}
        self.direction_string_map[Port.Direction.IN] = "input"
        self.direction_string_map[Port.Direction.OUT] = "output"
        self.direction_string_map[Port.Direction.INOUT] = "inout"
        self.direction_string_map[Port.Direction.UNDEFINED] = "/* undefined port direction */ inout"
        self.written = set()
        self.indent_count = 4  # set the indentation level for various components
        self.write_blackbox = write_blackbox
        self.definition_list = definition_list
        self.skip_constraints = skip_constraints
        self.sort_all = sort_all
        self.show_assign_instance_name = show_assign_instance_name

    def run(self, ir, file_out="out.v"):
        self._open_file(file_out)
        self._compose(ir)

    def _open_file(self, file_name):
        f = open(file_name, "w")
        self.file = f

    def _compose(self, netlist):
        self._write_header(netlist)
        instance = netlist.top_instance
        if instance is not None:
            if self.reverse:
                self._write_from_bottom(instance)
            else:
                self._write_from_top(instance)
        for library in netlist.libraries:
            for definition in library.definitions:
                if definition not in self.written:
                    self._write_module(definition)

    def _sorted(self, iterator, sort_by):
        return sorted(iterator, key=lambda x: sort_by.format(x=x)) \
            if self.sort_all else iterator

    def _write_header(self, netlist):
        self.file.write("//Generated from netlist by SpyDrNet\n")
        self.file.write("//netlist name: " + self._fix_name(netlist.name) + "\n")

    def _write_from_top(self, instance):
        # self.written = set()
        to_write = deque()
        to_write.append(instance.reference)
        while len(to_write) != 0:
            definition = to_write.popleft()
            if definition in self.written:
                continue
            self.written.add(definition)
            for c in self._sorted(definition.children, "{x.reference.name}_{x.name}"):
                if c.reference not in self.written:
                    to_write.append(c.reference)
            assert definition.name is not None, self._error_string(
                "definition has no name set", definition
            )
            self._write_module(definition)

    ###########################################################################
    # Write verilog constructs
    ###########################################################################

    def _write_preprocessor_directives(self, module):
        """write out the backtick preprocessor directives.
        this will likely just be `timescale 1 ps / 1 ps

        UPDATE: I'm just going to skip this for now.
        It can be added if simulation support is needed later"""
        pass  # not currently implemented, just pass

    def _write_star_constraints(self, o):
        if "VERILOG.InlineConstraints" in o and \
                len(o["VERILOG.InlineConstraints"]) != 0 and \
                self.skip_constraints == False:
            dictionary = o["VERILOG.InlineConstraints"]
            self.file.write(vt.OPEN_PARENTHESIS)
            self.file.write(vt.STAR)
            self.file.write(vt.SPACE)
            first = ""
            for k, v in dictionary.items():
                if v is not None:
                    self.file.write(first + k + vt.SPACE +
                                    vt.EQUAL + vt.SPACE + str(v))
                else:
                    self.file.write(first + k)
                first = vt.COMMA + vt.SPACE
            self.file.write(vt.SPACE)
            self.file.write(vt.STAR)
            self.file.write(vt.CLOSE_PARENTHESIS)
            self.file.write(vt.NEW_LINE)

    def _write_bundle_with_indicies(self, bundle, low, high):
        """write out a bundle name and indicies. in name indicies order.
        useful for cable and port instances"""
        self._write_name(bundle)
        self._write_brackets(bundle, low, high)

    def _write_module(self, definition):
        """write the constraints then the module header then the module body"""
        if self.definition_list:
            if not definition.name in self.definition_list:
                return
        if definition.library.name == "SDN_VERILOG_ASSIGNMENT":
            return  # don't write assignment definitions
        if definition.library.name == "hdi_primitives":
            if not self.write_blackbox:
                return
            self.file.write(vt.CELL_DEFINE)
            self.file.write(vt.NEW_LINE)
        self._write_star_constraints(definition)
        self._write_module_header(definition)
        self._write_module_body(definition)
        self.file.write(vt.END_MODULE)
        if definition.library.name == "hdi_primitives":
            self.file.write(vt.NEW_LINE)
            self.file.write(vt.END_CELL_DEFINE)

        self.file.write(2 * vt.NEW_LINE)

    def _write_module_header(self, definition):
        """write out the module header with the following style:
        module module_name (port_name, port_name);
        start with module and end with semi colon
        """
        self.file.write(vt.MODULE)
        self.file.write(vt.SPACE)
        self._write_name(definition)
        self.file.write(vt.NEW_LINE)
        if "VERILOG.Parameters" in definition:
            self._write_module_parameters(definition)
        self._write_module_header_ports(definition)
        self.file.write(vt.NEW_LINE)

    def _write_module_body(self, definition):
        """write out the module body start with ports, then do assignments then instances"""
        self._write_module_body_ports(definition)
        if definition.library.name != "hdi_primitives":
            self._write_module_body_cables(definition)
            self._write_assignments(definition)
            self._write_module_body_instances(definition)

    def _write_module_body_instances(self, definition):
        for c in definition.children:
            self._write_module_body_instance(c)

    def _write_module_body_instance(self, instance):
        if instance.reference.library.name == "SDN_VERILOG_ASSIGNMENT":
            return  # do not write the assignment instance
        self._write_star_constraints(instance)
        self.file.write(self.indent_count * vt.SPACE)
        self._write_name(instance.reference)
        self.file.write(vt.SPACE)
        if not self.defparam:
            if "VERILOG.Parameters" in instance:
                self._write_instance_parameters(instance)
                self.file.write(self.indent_count * vt.SPACE)
        self._write_name(instance)
        self.file.write(vt.NEW_LINE)
        self._write_instance_ports(instance)
        self.file.write(vt.NEW_LINE)
        if self.defparam:
            if "VERILOG.Parameters" in instance:
                for key, value in instance["VERILOG.Parameters"].items():
                    to_write = (self.indent_count * vt.SPACE) + vt.DEFPARAM + vt.SPACE
                    to_write += self._fix_name(instance.name) + vt.DOT + key + vt.EQUAL
                    to_write += value + vt.SEMI_COLON + vt.NEW_LINE
                    self.file.write(to_write)

    def _write_module_body_ports(self, definition):
        for p in self._sorted(definition.ports, "{x.direction}_{x.name}"):
            self._write_module_body_port(p)
        self.file.write(vt.NEW_LINE)

    def _write_module_body_port(self, port):
        _, cables = self._all_wires_and_cables_from_pinset(port.pins)
        if len(cables) == 0:
            # adding the port will let composer to still print out disconnected ports
            cables.append(port)
        for c in self._sorted(cables, "{x.name}"):
            self._write_star_constraints(port)
            self.file.write(self.indent_count * vt.SPACE)
            self.file.write(self.direction_string_map[port.direction])
            self.file.write(vt.SPACE)
            self._write_brackets_defining(c)
            self._write_name(c)
            self.file.write(vt.SEMI_COLON)
            self.file.write(vt.NEW_LINE)

    def _write_module_body_cables(self, definition):
        for c in self._sorted(definition.cables, "{x.name}"):
            self._write_module_body_cable(c)
        self.file.write(vt.NEW_LINE)

    def _write_module_body_cable(self, cable):
        self._write_star_constraints(cable)
        self.file.write(self.indent_count * vt.SPACE)
        if "VERILOG.CableType" in cable:
            self.file.write(cable["VERILOG.CableType"])
        else:
            self.file.write(vt.WIRE)
        self.file.write(vt.SPACE)
        self._write_brackets_defining(cable)
        self._write_name(cable)
        self.file.write(vt.SEMI_COLON)
        self.file.write(vt.NEW_LINE)

    def _write_concatenation(self, wires):
        """write out the concatenation statement
        {wire_1, wire_2}"""
        self.file.write(vt.OPEN_BRACE)
        first = True
        previous_cable = Cable()
        first_index = 0
        previous_index = 0
        has_to_write = False
        for w in wires:
            if w is not None:
                index = self._index_of_wire_in_cable(w)
                if w.cable.name == previous_cable.name:
                    if index == (previous_index - 1):
                        previous_index = index
                    else:
                        # write the previous and save new stuff
                        if not first:
                            self.file.write(vt.COMMA)
                            self.file.write(vt.SPACE)
                        self._write_bundle_with_indicies(
                            previous_cable, previous_index, first_index
                        )
                        first = False
                        previous_cable = w.cable
                        first_index = index
                        previous_index = index
                else:
                    if has_to_write:
                        # write the previous and save new stuff
                        if not first:
                            self.file.write(vt.COMMA)
                            self.file.write(vt.SPACE)
                        self._write_bundle_with_indicies(
                            previous_cable, previous_index, first_index
                        )
                        first = False
                    previous_cable = w.cable
                    first_index = index
                    previous_index = index
                has_to_write = True
            else:
                None
                # break
        if has_to_write:
            if not first:
                self.file.write(vt.COMMA)
                self.file.write(vt.SPACE)
            self._write_bundle_with_indicies(
                previous_cable, previous_index, first_index
            )

        self.file.write(vt.CLOSE_BRACE)

    def _write_module_header_ports(self, definition):
        self.file.write(vt.OPEN_PARENTHESIS)
        first = True
        for p in self._sorted(definition.ports, "{x.name}"):
            if not first:
                self.file.write(vt.COMMA)
            self.file.write(vt.NEW_LINE)
            self._write_module_header_port(p)
            first = False
        self.file.write(vt.NEW_LINE)
        self.file.write(vt.CLOSE_PARENTHESIS)
        self.file.write(vt.SEMI_COLON)
        self.file.write(vt.NEW_LINE)

    def pin_sort_func(self, p):
        if isinstance(p, sdn.OuterPin):
            return p.inner_pin.port.pins.index(p.inner_pin)
        return p.port.pins.index(p)

    def _write_module_header_port(self, port):
        '''does not write the input output or width,
        check for concatenation port as well'''
        self.file.write((self.indent_count * vt.SPACE))
        aliased = self._is_pinset_concatenated(port.pins, port.name)
        if aliased:
            wires = []
            pin_list = list(p for p in port.pins)
            pin_list.sort(reverse=True, key=self.pin_sort_func)
            for pin in pin_list:
                wires.append(pin.wire)
            self.file.write(vt.DOT)
            self._write_name(port)
            self.file.write(vt.OPEN_PARENTHESIS)
            self._write_concatenation(wires)
            self.file.write(vt.CLOSE_PARENTHESIS)
        else:
            self._write_name(port)

    def _write_assignments(self, definition):
        for c in self._sorted(definition.children, "{x.reference.name}_{x.name}"):
            if c.reference.library.name == "SDN_VERILOG_ASSIGNMENT":
                self._write_assignment(c)

    def _write_assignment(self, instance):
        """take an assignment instance and write an assignment out
        assign cable_out = cable_in;"""
        in_port = None
        out_port = None
        for p in instance.reference.ports:
            if p.name == "o":
                out_port = p
            if p.name == "i":
                in_port = p
        assert in_port is not None, self._error_string(
            "instance does not appear to be an assignment with a port named i and o",
            instance,
        )
        assert out_port is not None, self._error_string(
            "instance does not appear to be an assignment with a port named i and o",
            instance,
        )
        left_wires = []
        right_wires = []
        in_pins = []
        out_pins = []
        for p in in_port.pins:
            in_pins.append(instance.pins[p])
        for p in out_port.pins:
            out_pins.append(instance.pins[p])
        in_pins.sort(reverse=False, key=self.pin_sort_func)
        out_pins.sort(reverse=True, key=self.pin_sort_func)
        in_wires, in_cables = self._all_wires_and_cables_from_pinset(in_pins)
        out_wires, out_cables = self._all_wires_and_cables_from_pinset(
            out_pins)
        assert not self._is_pinset_concatenated(in_pins, in_wires[0].cable.name), self._error_string(
            "multiple cables appear to be connected to a single assignment input", instance)
        assert not self._is_pinset_concatenated(out_pins, out_wires[0].cable.name), self._error_string(
            "multiple cables appear to be connected to a single assignment output", instance)
        self.file.write(vt.ASSIGN)
        self.file.write(vt.SPACE)
        hi = self._index_of_wire_in_cable(out_wires[-1])
        li = self._index_of_wire_in_cable(out_wires[0])
        self._write_bundle_with_indicies(out_cables[0], li, hi)
        self.file.write(vt.SPACE)
        self.file.write(vt.EQUAL)
        self.file.write(vt.SPACE)

        if self._is_pinset_concatenated(in_pins, in_pins[0].wire.cable.name):
            self._write_concatenation(in_wires)
        else:
            if len(in_wires) > 1:
                self.file.write(vt.OPEN_BRACE)
            i = 0
            for w in in_wires:
                li = self._index_of_wire_in_cable(w)
                hi = None
                self._write_bundle_with_indicies(w.cable, li, hi)
                if i < len(in_wires)-1:
                    self.file.write(vt.COMMA)
                    self.file.write(vt.SPACE)
                i+=1
            if len(in_wires) > 1:
                self.file.write(vt.CLOSE_BRACE)

        self.file.write(vt.SEMI_COLON)
        if self.show_assign_instance_name:
            self.file.write(f" // {instance.name}[{instance.reference.name}]")
        self.file.write(vt.NEW_LINE)

    def _write_module_parameters(self, definition):
        """write out the parameters in the module header"""
        self.file.write(vt.OCTOTHORP)
        self.file.write(vt.OPEN_PARENTHESIS)
        indentation = "\n    "
        first = True
        for k, v in definition["VERILOG.Parameters"].items():
            if not first:
                self.file.write(vt.COMMA)
            self.file.write(indentation)
            self.file.write(vt.PARAMETER)
            self.file.write(vt.SPACE)
            self.file.write(k)
            if v is not None:
                self.file.write(" " + vt.EQUAL + " ")
                self.file.write(v)
            first = False
        self.file.write(vt.NEW_LINE)
        self.file.write(vt.CLOSE_PARENTHESIS)

    def _write_instance_parameters(self, instance):
        """write out the parameters in the instance
        #(
        .key(value),
        ...
        )"""
        self.file.write(vt.OCTOTHORP)
        self.file.write(vt.OPEN_PARENTHESIS)
        self.file.write(vt.NEW_LINE)
        first = True
        for k, v in instance["VERILOG.Parameters"].items():
            if not first:
                self.file.write(vt.COMMA)
                self.file.write(vt.NEW_LINE)
            self._write_instance_parameter(k, v)
            first = False
        self.file.write(vt.NEW_LINE)
        self.file.write(self.indent_count * vt.SPACE)
        self.file.write(vt.CLOSE_PARENTHESIS)
        self.file.write(vt.NEW_LINE)

    def _write_instance_parameter(self, key, value):
        self.file.write(2 * self.indent_count * vt.SPACE)
        self.file.write(vt.DOT)
        self.file.write(key)
        self.file.write(vt.OPEN_PARENTHESIS)
        self.file.write(value)
        self.file.write(vt.CLOSE_PARENTHESIS)

    def _write_instance_ports(self, instance):
        """write out the port mapping on an instance."""
        self.file.write(self.indent_count * vt.SPACE)
        self.file.write(vt.OPEN_PARENTHESIS)
        self.file.write(vt.NEW_LINE)
        first = True
        for p in self._sorted(instance.reference.ports, "{x.name}"):
            if not first:
                self.file.write(vt.COMMA)
                self.file.write(vt.NEW_LINE)
            if p.name:
                self._write_instance_port(instance, p)
            else:
                self._write_implicitly_mapped_instance_port(instance, p)
            first = False
        self.file.write(vt.NEW_LINE)
        self.file.write(self.indent_count * vt.SPACE)
        self.file.write(vt.CLOSE_PARENTHESIS)
        self.file.write(vt.SEMI_COLON)

    def _write_implicitly_mapped_instance_port(self, instance, port):
        """
        Ports that have no name must be implicitly mapped. E.g. inst(VCC_net) rather than
        inst(.p(VCC_net))
        """
        self.file.write(2 * self.indent_count * vt.SPACE)
        # self.file.write(vt.DOT)
        # self._write_name(port)
        # self.file.write(vt.OPEN_PARENTHESIS)
        pins = []
        is_downto = True
        for p in port.pins:
            pins.append(instance.pins[p])
        if pins[0].wire is not None:
            name = pins[0].wire.cable.name
            is_downto = pins[0].wire.cable.is_downto
        else:
            name = None
        concatenated = self._is_pinset_concatenated(pins, name, is_downto)
        wires = []
        pin_list = list(p for p in port.pins)
        pin_list.sort(reverse=True, key=self.pin_sort_func)
        for pin in pin_list:
            wires.append(pin.wire)
        if concatenated:
            self._write_concatenation(wires)
        else:
            if pins[0].wire is not None:
                last = -1
                wl = wires[last]
                wr = wires[0]
                while wl is None:  # get the last named non none wire.
                    last = last - 1
                    wl = wires[last]
                il = self._index_of_wire_in_cable(wl)
                ir = self._index_of_wire_in_cable(wr)
                self._write_bundle_with_indicies(wl.cable, ir, il)

        # self.file.write(vt.CLOSE_PARENTHESIS)

    def _write_instance_port(self, instance, port):
        self.file.write(2 * self.indent_count * vt.SPACE)
        self.file.write(vt.DOT)
        self._write_name(port)
        self.file.write(vt.OPEN_PARENTHESIS)
        pins = []
        is_downto = True
        for p in port.pins:
            pins.append(instance.pins[p])
        if pins[0].wire is not None:
            name = pins[0].wire.cable.name
            is_downto = pins[0].wire.cable.is_downto
        else:
            name = None
        concatenated = self._is_pinset_concatenated(pins, name, is_downto)
        wires = []
        sorted_wires = []
        pin_list = list(p for p in pins)
        pin_list.sort(reverse=True, key=self.pin_sort_func)
        for pin in pin_list:
            sorted_wires.append(pin.wire)
        for p in pins:
            wires.append(p.wire)
        if concatenated:
            self._write_concatenation(sorted_wires)
        else:
            if pins[0].wire is not None:
                last = -1
                wl = wires[last]
                wr = wires[0]
                while wl is None:  # get the last named non none wire.
                    last = last - 1
                    wl = wires[last]
                il = self._index_of_wire_in_cable(wl)
                ir = self._index_of_wire_in_cable(wr)
                self._write_bundle_with_indicies(wl.cable, ir, il)

        self.file.write(vt.CLOSE_PARENTHESIS)

    def _write_name(self, o):
        '''write the name of an o. this is split out to give an error message if the name is not set
        In the future this could be changed to add a name to os that do not have a name set'''
        assert o.name is not None, self._error_string(
            "name of o is not set", o)
        if o.name[0] == '\\':
            assert o.name[-1] == ' ', self._error_string(
                "the o name starts with escape and does not end with a space.", o)
        self.file.write(o.name)

    def _write_brackets_defining(self, bundle):
        """write the brackets for port or cable definitions"""
        if isinstance(bundle, Cable):
            array = bundle.wires
        elif isinstance(bundle, Port):
            array = bundle.pins
        width = len(array)

        assert width != 0, self._error_string(
            "bundle has 0 width, this will not write correctly please add a \
            pin to the port or wire to the cable.",
            bundle,
        )

        if width == 1 and bundle.lower_index == 0:
            return  # no need to write because this is assumed
        self.file.write(vt.OPEN_BRACKET)
        if bundle.is_downto:
            self.file.write(str(bundle.lower_index + width - 1))
            self.file.write(vt.COLON)
            self.file.write(str(bundle.lower_index))
        else:
            self.file.write(str(bundle.lower_index))
            self.file.write(vt.COLON)
            self.file.write(str(bundle.lower_index + width - 1))

        self.file.write(vt.CLOSE_BRACKET)

    def _write_brackets(self, bundle, low_index, high_index):
        """write a bundle's brackets based on the low and high indicies given
        does not write out the name, works on both cables and ports"""
        if low_index is None and high_index is None:
            return  # nothing to write.

        if isinstance(bundle, Cable):
            array = bundle.wires
        elif isinstance(bundle, Port):
            array = bundle.pins
        width = len(array)
        assert width != 0, self._error_string("cannot index into 0 width cable")
        lower_bundle = bundle.lower_index
        upper_bundle = lower_bundle + width - 1

        # intended logic
        # the bundle is a single bit: assert indicies are within but nothing to be written
        # the bundle is multibit and the indicies match the upper and lower(or none): nothing to be written
        # the bundle is multibit but the indicies match each other or one is none: write a single index
        # the bundle is multibit but the indicies don't match each other: write both indicies

        if width == 1:
            assert (low_index == None or low_index == lower_bundle), \
                self._error_string(
                    "attempted to index bundle out of bounds at " + str(low_index), bundle)
            assert (high_index == None or high_index == upper_bundle), \
                self._error_string(
                    "attempted to index bundle out of bounds at " + str(high_index), bundle)
            return
        elif (low_index == lower_bundle and high_index == upper_bundle and bundle.is_downto) or (
            low_index == upper_bundle and high_index == lower_bundle and not bundle.is_downto) or (
            low_index is None and high_index is None):
            self.file.write("[" + str(high_index) + ":" + str(low_index) + "]")
            return
        elif low_index == high_index or low_index is None or high_index is None:
            index = low_index
            if index is None:
                index = high_index
            # this assertion checks the logic of this if statement
            assert index is not None, self._error_string(
                "if both high and low indicies are None no brackets need to be written", bundle)
            # the following assertion will check the inputs to the function
            assert index >= lower_bundle and index <= upper_bundle,\
                self._error_string(
                    "attempted to write an index out of bounds: " + str(index), bundle)
            self.file.write("[" + str(index) + "]")
        else:
            # first assertion is an internal error, check the if elif logic here.
            assert low_index != high_index and low_index is not None and high_index is not None,\
                self._error_string(
                    "a single value needs to be written if any of these conditions are true ", bundle)
            # these assertions highlight issues with the input to the function
            assert low_index >= lower_bundle and low_index <= upper_bundle,\
                self._error_string(
                    "attempted to write an index out of bounds: " + str(low_index), bundle)
            assert high_index >= lower_bundle and high_index <= upper_bundle,\
                self._error_string(
                    "attempted to write an index out of bounds: " + str(high_index), bundle)
            if bundle.is_downto:
                self.file.write(
                    "[" + str(high_index) + ":" + str(low_index) + "]")
            else:
                self.file.write(
                    "[" + str(low_index) + ":" + str(high_index) + "]")

    ###############################################################################
    # helper functions for composing
    ###############################################################################

    def _index_of_wire_in_cable(self, wire):
        index = 0
        for w in wire.cable.wires:
            if w == wire:
                return index + wire.cable.lower_index
            index += 1
        return None

    def _is_pinset_concatenated(self, pins, name, is_downto=1):
        aliased = False
        now_none = False
        last_index = None
        for p in pins:
            if p.wire is None:
                next_name = None
                now_none = True
            else:
                next_name = p.wire.cable.name
                if now_none is True:
                    aliased = True
                index = self._index_of_wire_in_cable(p.wire)
                if last_index is None:
                    last_index = index
                else:
                    if (index-last_index) != (1, -1)[is_downto]:
                        aliased = True
                        break
                last_index = index
            if next_name != name and not now_none:
                aliased = True
                break

        return aliased

    def _all_wires_and_cables_from_pinset(self, pins):
        wires = []
        cables = []
        for p in pins:
            wires.append(p.wire)
            if p.wire is not None and p.wire.cable not in cables:
                cables.append(p.wire.cable)
        return wires, cables

    def _error_string(self, message, o):
        return "compose error: " + message + str(o)

    def _write_escapable_name(self, str_in):
        if str_in[0] == "\\":
            self.file.write(str_in + " ")
        else:
            self.file.write(str_in)
