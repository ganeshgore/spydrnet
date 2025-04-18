# Copyright 2021 Dallin Skouson, BYU CCL
# please see the BYU CCl SpyDrNet license file for terms of usage.


from spydrnet.parsers.verilog.tokenizer import VerilogTokenizer, VerilogTokenizerSimple
import spydrnet.parsers.verilog.verilog_tokens as vt
from spydrnet.ir import Netlist, Definition, Instance, OuterPin
from spydrnet.plugins import namespace_manager
import spydrnet as sdn
import re

class VerilogParser:
    """
    Parse verilog files into spydrnet.

    Higher level functions will always peek when deciding what lower level function to call.
    within your own function call next instead to keep the flow moving.

    the first token to expect in a function will be the token that starts that construct.
    """

    #########################################################
    # Note to contributors
    #########################################################
    # I have tried to follow the convention that each function
    # parses all of the construct it is designed to parse
    # for example the parse module function will parse the
    # module keyword and then will call the parse
    # instance function. It will not consume any of the tokens
    # that belong to the instance instantations including the
    # semi colon. (it just uses peek)
    #
    # I would suggest following this convention even on constructs
    # where the first word is always the same.
    # the small overhead of using the peek function to not consume
    # the token has been well worth making it easier to maintain.
    # --Dallin

    #########################################################
    # helper classes
    #########################################################

    class BlackboxHolder:
        """this is an internal class that helps manage
        modules that are instanced before they are declared"""

        def __init__(self):
            self.name_lookup = {}
            self.defined = set()

        def get_blackbox(self, name):
            """creates or returns the black box based on the name"""
            if name in self.name_lookup:
                return self.name_lookup[name]
            else:
                definition = Definition()
                definition.name = name
                self.name_lookup[name] = definition
                return definition

        def define(self, name):
            """adds the name to the defined set"""
            self.defined.add(self.name_lookup[name])

        def get_undefined_blackboxes(self):
            """return an iterable of all undefined blackboxes"""
            undef = set()
            for v in self.name_lookup.values():
                if v not in self.defined:
                    undef.add(v)
            return undef

    #######################################################
    # setup functions
    #######################################################
    @staticmethod
    def from_filename(filename):
        parser = VerilogParser()
        parser.filename = filename
        return parser

    @staticmethod
    def from_file_handle(file_handle):
        parser = VerilogParser()
        parser.filename = file_handle
        return parser

    def __init__(self):
        self.filename = None
        self.tokenizer = None

        self.netlist = None
        self.current_library = None
        self.current_definition = None
        self.current_instance = None

        self.primitives = None
        self.work = None
        self.assigns = None
        self.assignment_count = 0

        self.blackbox_holder = self.BlackboxHolder()

        self.implicitly_mapped_ports = {}

    def parse(self):
        """parse a verilog netlist represented by verilog file

        verilog_file can be a filename or stream
        """
        self.initialize_tokenizer()
        ns_default = namespace_manager.default
        namespace_manager.default = "DEFAULT"
        self.parse_verilog()
        namespace_manager.default = ns_default
        self.tokenizer.__del__()
        return self.netlist

    def initialize_tokenizer(self):
        self.tokenizer = VerilogTokenizer(self.filename)

    def peek_token(self):
        token = self.peek_token_remove_comments()
        if token[0] == "`":
            t_split = token.split(maxsplit=1)
            if len(t_split) > 1 and t_split[0] in [vt.IFDEF]:
                while t_split[0] != vt.ENDIF:
                    token = self.next_token_remove_comments()
                    t_split = token.split(maxsplit=1)
                token = self.peek_token_remove_comments()
            if len(t_split) > 1 and t_split[0] == vt.DEFINE:
                assert False, self.error_string(
                    "define not supported",
                    "assumes all macros are undefined",
                    vt.DEFINE,
                )
        return token

    def next_token(self):
        token = self.next_token_remove_comments()
        if token[0] == "`":
            t_split = token.split(maxsplit=1)
            if len(t_split) > 1 and t_split[0] in [vt.IFDEF]:
                while t_split[0] != vt.ENDIF:
                    token = self.next_token_remove_comments()
                    t_split = token.split(maxsplit=1)
                token = self.next_token_remove_comments()
            if len(t_split) > 1 and t_split[0] == vt.DEFINE:
                assert False, self.error_string(
                    "define not supported",
                    "assumes all macros are undefined",
                    vt.DEFINE,
                )
        return token

    def peek_token_remove_comments(self):
        """peeks from the tokenizer this wrapper function exists to skip comment tokens"""
        token = self.tokenizer.peek()
        while (
            len(token) >= 2 and token[0] == "/" and (token[1] == "/" or token[1] == "*")
        ):
            # this is a comment token skip it
            self.tokenizer.next()
            token = self.tokenizer.peek()
        return token

    def next_token_remove_comments(self):
        """peeks from the tokenizer this wrapper function exists to skip comment tokens"""
        token = self.tokenizer.next()
        while len(token) >= 2 and (
            token[0:2] == vt.OPEN_LINE_COMMENT or token[0:2] == vt.OPEN_BLOCK_COMMENT
        ):
            # this is a comment token, skip it
            token = self.tokenizer.next()
        return token

    #######################################################
    # parsing functions
    #######################################################

    def parse_verilog(self):
        self.netlist = Netlist()
        self.netlist.name = "SDN_VERILOG_NETLIST"
        self.work = self.netlist.create_library("work")
        self.primitives = self.netlist.create_library("hdi_primitives")
        self.current_library = self.work

        preprocessor_defines = set()
        star_properties = {}
        time_scale = None
        primitive_cell = False

        while self.tokenizer.has_next():
            token = self.peek_token()
            if token.split(maxsplit=1)[0] == vt.CELL_DEFINE:
                primitive_cell = True
                self.current_library = self.primitives
                # token = token.split(maxsplit = 1)[1]
                token = self.next_token()
            elif token.split(maxsplit=1)[0] == vt.END_CELL_DEFINE:
                primitive_cell = False
                self.current_library = self.work
                # token = token.split(maxsplit = 1)[1]
                token = self.next_token()

            elif token == vt.MODULE:
                if primitive_cell:
                    self.parse_primitive()
                    if self.peek_token() in (vt.END_PRIMITIVE, vt.END_MODULE):
                        token = self.next_token()
                else:
                    self.parse_module()
                # go ahead and set the extra metadata that we collected to this point
                if time_scale is not None:
                    self.current_definition["VERILOG.TimeScale"] = time_scale
                if len(star_properties.keys()) > 0:
                    self.current_definition[
                        "VERILOG.InlineConstraints"
                    ] = star_properties
                    star_properties = {}

            elif token == vt.PRIMITIVE:
                # self.parse_primitive()
                # if time_scale is not None:
                #     self.current_definition["VERILOG.TimeScale"] = time_scale
                # if len(star_properties.keys()) > 0:
                #     self.current_definition["VERILOG.InlineConstraints"] = star_properties
                #     star_properties = {}
                star_properties = {}
                while token != vt.END_PRIMITIVE:
                    token = self.next_token()

            elif token == vt.DEFINE:
                assert False, "Currently `define is not supported"
            elif token == vt.IFDEF:
                token = self.next_token()
                token = self.next_token()
                if token not in preprocessor_defines:
                    while token != vt.ENDIF:
                        token = self.next_token()
            elif token == vt.OPEN_PARENTHESIS:
                stars = self.parse_star_property()
                for k, v in stars.items():
                    star_properties[k] = v

            elif token.split(maxsplit=1)[0] == vt.TIMESCALE:
                token = self.next_token()
                time_scale = token.split(maxsplit=1)[1]
            elif token.split(maxsplit=1)[0] == vt.DEFUALT_NETTYPE:
                token = self.next_token()
            else:
                pass
                assert False, self.error_string(
                    "something at the top level of the file",
                    "got unexpected token",
                    token,
                )

        self.add_blackbox_definitions()

        self.connect_implicitly_mapped_ports()

        return self.netlist

    def add_blackbox_definitions(self):
        self.current_library = self.primitives
        for d in self.blackbox_holder.get_undefined_blackboxes():
            d["VERILOG.primitive"] = True
            self.current_library.add_definition(d)

    def parse_primitive(self, definition_list=[], bypass_name_check=False):
        """
        similar to parse module but it will only look for the inputs and outputs to get an idea of
        how those things look

        definition_list is an optional parameter that is used by primitive_library_reader as
        primitive libraries are parsed. If the primitive name is not in the definition list, it is
        not needed and will be skipped.
        """
        token = self.next_token()
        assert token == vt.MODULE or token == vt.PRIMITIVE, self.error_string(
            vt.MODULE, "to begin module statement", token
        )
        token = self.next_token()
        if not bypass_name_check:
            assert vt.is_valid_identifier(token), self.error_string(
                "identifier", "not a valid module name", token
            )
        name = token.strip()

        if definition_list:
            if name not in definition_list:  # we don't need this primitive info
                while token != vt.END_MODULE:
                    token = self.next_token()
                # self.next_token()
                return

        definition = self.blackbox_holder.get_blackbox(name)
        self.blackbox_holder.define(name)
        self.current_library.add_definition(definition)
        self.current_definition = definition

        # uses the same header parser because the primitives and regular cells have the same header.
        self.parse_module_header()

        self.parse_primitive_body()

    def parse_primitive_body(self):
        """just look for port information, skip tasks and functions to help out."""

        token = self.peek_token()

        while token != vt.END_MODULE and token != vt.END_PRIMITIVE:
            token = self.peek_token()
            if (
                token == vt.FUNCTION
            ):  # these constructs may contain input output or inout
                while token != vt.END_FUNCTION:
                    token = self.next_token()
            elif token == vt.TASK:  # these constructs may contain input output or inout
                while token != vt.END_TASK:
                    token = self.next_token()
            elif token in vt.PORT_DIRECTIONS:
                self.parse_port_declaration({})
            else:
                token = self.next_token()

    def parse_module(self):
        token = self.next_token()
        assert token == vt.MODULE, self.error_string(
            vt.MODULE, "to begin module statement", token
        )
        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "identifier", "not a valid module name", token
        )
        name = token.strip()

        definition = self.blackbox_holder.get_blackbox(name)
        self.blackbox_holder.define(name)
        self.current_library.add_definition(definition)
        self.current_definition = definition
        self.assignment_count = 0
        if self.netlist.top_instance is None:
            self.netlist.top_instance = Instance()
            self.netlist.top_instance.name = definition.name + "_top"
            self.netlist.top_instance.reference = definition
            self.netlist.name = "SDN_VERILOG_NETLIST_" + definition.name

        self.parse_module_header()

        self.parse_module_body()

    def parse_module_header(self):
        """parse a module header and add the parameter dictionary and port list to the
        current_definition"""
        token = self.peek_token()
        if token == "#":
            self.parse_module_header_parameters()

        token = self.peek_token()
        assert token == "(", self.error_string("(", "for port mapping", token)

        self.parse_module_header_ports()

        token = self.next_token()
        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "to end the module ports in the header", token
        )

        token = self.next_token()
        assert token == vt.SEMI_COLON, self.error_string(
            vt.SEMI_COLON, "to end the module header section", token
        )

    def parse_module_header_parameters(self):
        """parse a parameter block in a module header, add all parameters to the current
        definition"""
        token = self.next_token()
        assert token == vt.OCTOTHORP, self.error_string(
            vt.OCTOTHORP, "to begin parameter map", token
        )
        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to begin parameter map", token
        )

        token = self.next_token()

        parameter_dictionary = {}

        while token != ")":
            # this is happening twice for all but the first one.. could simplify
            assert token == vt.PARAMETER, self.error_string(
                vt.PARAMETER, "parameter declaration", token
            )

            key, value = self.parse_parameter_keyvalue()

            parameter_dictionary[key] = value
            token = self.next_token()
            if token == vt.COMMA:  # just keep going
                token = self.next_token()
                assert token == vt.PARAMETER, self.error_string(
                    vt.PARAMETER, "after comma in parameter map", token
                )
            else:
                assert token == vt.CLOSE_PARENTHESIS, self.error_string(
                    vt.CLOSE_PARENTHESIS, "to end parameter declarations", token
                )

        self.set_definition_parameters(self.current_definition, parameter_dictionary)

    def parse_body_parameter_declarations(self):
        """parse a parameters definition structure and add them to the module

        this looks like:

        parameter [2:0] PARAM1 = 3'b110, PARAM2 = "false";

        and must come after the associated module
        """

        token = self.next_token()
        assert token == vt.PARAMETER, self.error_string(
            vt.PARAMETER, "to being parameter statement", token
        )

        token = self.peek_token()
        parameter_dictionary = {}

        while token != vt.SEMI_COLON:
            key, value = self.parse_parameter_keyvalue()
            parameter_dictionary[key] = value

            token = self.next_token()
            assert token == vt.SEMI_COLON or token == vt.COMMA, self.error_string(
                ',;', "after parameter declaration", token
            )

        assert len(parameter_dictionary) > 0, self.error_string(
            'declarations', "in parameter declaration", token
        )

        self.set_definition_parameters(self.current_definition, parameter_dictionary)

    def parse_parameter_keyvalue(self):
        """parses and returns key name and assigned value of a parameter declaration"""

        key = ""
        token = self.peek_token()
        if token == vt.OPEN_BRACKET:
            left, right = self.parse_brackets()
            if right is not None:
                key = "[" + str(left) + ":" + str(right) + "] "
            else:
                key = "[" + str(left) + "] "

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "identifer", "in parameter list", token
        )
        key += token.strip()

        token = self.next_token()
        if key == vt.INTEGER:
            key += " " + token
            token = self.next_token()

        assert token == vt.EQUAL, self.error_string(
            vt.EQUAL, "in parameter list", token
        )

        token = self.next_token()
        # not really sure what to assert here.
        value = token

        return key, value

    def parse_module_header_ports(self):
        """parse port declarations in the module header and add them to the definition"""
        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to begin port declarations", token
        )

        token = self.peek_token()

        while token != ")":
            # the first token could be a name or input output or inout
            if token == ".":
                self.parse_module_header_port_alias()
            else:
                self.parse_module_header_port()
            token = self.peek_token()
            if token != vt.CLOSE_PARENTHESIS:
                assert token == vt.COMMA, self.error_string(
                    vt.COMMA, "to separate port declarations", token
                )
                token = self.next_token()  # consume the comma token
                token = self.peek_token()  # setup the next token

    def parse_module_header_port_alias(self):
        """
        parse the port alias portion of the module header

        this parses the port alias section so that the port name is only a port and the mapped wires
        are the cables names that connect to that port.

        this requires that the cables names be kept in a dictionary to allow for setting the
        direction when the direction is given to the internal port names.

        example syntax
        .canale({\\canale[3] ,\\canale[2] ,\\canale[1] ,\\canale[0] }),"""

        token = self.next_token()
        assert token == vt.DOT, self.error_string(vt.DOT, "for port aliasing", token)
        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "identifier", "for port in port aliasing", token
        )
        name = token.strip()

        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "parethesis to enclose port aliasing", token
        )

        token = self.peek_token()
        if token == vt.OPEN_BRACE:
            wires = self.parse_cable_concatenation()
        else:
            cable_lr_list = self.parse_variable_instantiation()
            assert len(cable_lr_list) == 1, self.error_string(
                'one entity declaration', "port aliasing construct", token
            )

            cable, left, right = cable_lr_list[0]
            wires = self.get_wires_from_cable(cable, left, right)

        token = self.next_token()
        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "parethesis to end port aliasing construct", token
        )

        port = self.create_or_update_port(
            name, left_index=len(wires) - 1, right_index=0
        )

        # connect the wires to the pins
        assert len(port.pins) == len(
            wires
        ), "Internal Error: the pins in a created port and the number of wires the \
            aliased cable do not match up"

        pin_list = list(p for p in port.pins)
        pin_list.sort(reverse=True, key=self.pin_sort_func)
        for i in range(len(pin_list)):
            wires[i].connect_pin(pin_list[i])

    def parse_cable_concatenation(self):
        """
        parse a concatenation structure of cables, create the cables mentioned, and deal with
        indicies return a list of ordered wires that represents the cable concatenation
        example syntax
        {wire1, wire2, wire3, wire4}
        """
        token = self.next_token()
        assert token == vt.OPEN_BRACE, self.error_string(
            vt.OPEN_BRACE, "to start cable concatenation", token
        )
        token = self.peek_token()
        wires = []
        while token != vt.CLOSE_BRACE:
            cable_lr_list = self.parse_variable_instantiation()
            assert len(cable_lr_list) == 1, self.error_string(
                'one entity declaration', "cable concatenation", token
            )
            cable, left, right = cable_lr_list[0]
            wires_temp = self.get_wires_from_cable(cable, left, right)
            wires_temp.sort(reverse=True, key=self.wire_sort_func)
            for w in wires_temp:
                wires.append(w)
            token = self.next_token()
            if token != vt.COMMA:
                assert token == vt.CLOSE_BRACE, self.error_string(
                    vt.CLOSE_BRACE, "to end cable concatenation", token
                )
        return wires

    def wire_sort_func(self, w):
        return w.cable.wires.index(w)*([-1, 1][int(w.cable.is_downto)])

    def parse_module_header_port(self):
        """parse the port declaration in the module header"""
        token = self.peek_token()
        direction = None
        defining = False
        if token in vt.PORT_DIRECTIONS:
            token = self.next_token()
            direction = vt.string_to_port_direction(token)
            token = self.peek_token()
            defining = True

        left = None
        right = None
        if token == vt.OPEN_BRACKET:
            left, right = self.parse_brackets()

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "identifier", "for port declaration", token
        )
        name = token.strip()
        port = self.create_or_update_port(
            name,
            left_index=left,
            right_index=right,
            direction=direction,
            defining=defining,
        )

        # get the left and right out of the port (in case we got more information out of an instance?)
        if left is None and right is None:
            left = port.lower_index + len(port.pins) - 1
            right = port.lower_index
            if not port.is_downto:
                temp = left
                left = right
                right = temp

        cable = self.create_or_update_cable(
            name, left_index=left, right_index=right, defining=defining
        )

        # wire together the cables and the port
        assert len(port.pins) == len(cable.wires), self.error_string(
            "the pins in a created port and the number of wires in it's cable do not match up",
            "wires: " + str(len(cable.wires)),
            "pins: " + str(len(port.pins)),
        )

        pin_list = list(p for p in port.pins)
        pin_list.sort(reverse=False, key=self.pin_sort_func)
        for i in range(len(pin_list)):
            cable.wires[i].connect_pin(pin_list[i])

    def parse_module_body(self):
        """
        parse through a module body

        module bodies consist of port declarations, wire and reg declarations and instantiations

        expects port declarations to start with the direction and then include the cable type if
        provided
        """
        direction_tokens = [vt.INPUT, vt.OUTPUT, vt.INOUT]
        variable_tokens = [vt.WIRE, vt.REG, vt.TRI0, vt.TRI1]
        token = self.peek_token()
        params = {}
        while token != vt.END_MODULE:
            if token in direction_tokens:
                self.parse_port_declaration(params)
                params = {}
            elif token in variable_tokens:
                self.parse_cable_declaration(params)
                params = {}
            elif token == vt.PARAMETER:
                self.parse_body_parameter_declarations()
            elif token == vt.ASSIGN:
                assigns_list = self.parse_assign()
                for assign_tuple in assigns_list:
                    assert(len(assign_tuple) == 6)
                    o_cable, o_left, o_right, i_cable, i_left, i_right = assign_tuple
                    self.connect_wires_for_assign(
                        o_cable, o_left, o_right, i_cable, i_left, i_right)
            elif token == vt.DEFPARAM:
                self.parse_defparam_parameters()
            elif vt.is_valid_identifier(token):
                self.parse_instantiation(params)
                params = {}
            elif token == vt.OPEN_PARENTHESIS:
                stars = self.parse_star_property()
                for k, v in stars.items():
                    params[k] = v
            else:
                assert False, self.error_string(
                    "direction, reg, wire, star_properties, or instance identifier",
                    "in module body",
                    token,
                )

            token = self.peek_token()

        token = self.next_token()
        assert token == vt.END_MODULE, self.error_string(
            vt.END_MODULE, "to end the module body", token
        )

    def parse_port_declaration(self, properties):
        """parse the port declaration post port list."""
        token = self.next_token()
        assert token in vt.PORT_DIRECTIONS, self.error_string(
            "direction keyword", "to define port", token
        )
        direction = vt.string_to_port_direction(token)

        token = self.peek_token()
        if token in [vt.REG, vt.WIRE]:
            var_type = token
            token = self.next_token()
        else:
            var_type = None

        token = self.peek_token()
        if token == vt.OPEN_BRACKET:
            left, right = self.parse_brackets()
        else:
            left = None
            right = None

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "port identifier", "identify port", token
        )
        names = []
        names.append(token.strip())

        token = self.next_token()
        while token == vt.COMMA:
            token = self.next_token()
            names.append(token.strip())
            token = self.next_token()

        assert token == vt.SEMI_COLON, self.error_string(
            vt.SEMI_COLON, "to end port declaration", token
        )

        for name in names:
            cable = self.create_or_update_cable(
                name,
                left_index=left,
                right_index=right,
                var_type=var_type,
                defining=True,
            )

            port_list = self.get_all_ports_from_wires(
                self.get_wires_from_cable(cable, left, right)
            )

            assert len(port_list) > 0, self.error_string(
                "port name defined in the module header",
                "to declare a port",
                cable.name,
            )

            if len(port_list) > 1:
                for p in port_list:
                    port = self.create_or_update_port(p.name, direction=direction)
                    port["VERILOG.InlineConstraints"] = properties
            else:
                port = self.create_or_update_port(
                    port_list.pop().name,
                    left_index=left,
                    right_index=right,
                    direction=direction,
                    defining=True,
                )

            if len(cable.wires) > 1:
                self.connect_resized_port_cable(cable, port)

    def parse_cable_declaration(self, properties, var_type=None):
        if not var_type:
            token = self.next_token()
            assert token in [vt.REG, vt.WIRE, vt.TRI0, vt.TRI1], self.error_string(
                "reg, tri1, tri0, or wire", "for cable declaration", token
            )
            var_type = token
            self.parse_cable_declaration_helper(properties, var_type)

            token = self.next_token()
            while token == vt.COMMA:
                self.parse_cable_declaration_helper({}, var_type)
                token = self.next_token()

            assert token == vt.SEMI_COLON, self.error_string(
                vt.SEMI_COLON, "to end cable declaration", token
            )

    def parse_cable_declaration_helper(self, properties, var_type=None):
        token = self.peek_token()
        if token == vt.OPEN_BRACKET:
            left, right = self.parse_brackets()
        else:
            left = None
            right = None

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "valid cable identifier", "identify the cable", token
        )
        name = token.strip()

        cable = self.create_or_update_cable(
            name, left_index=left, right_index=right, var_type=var_type
        )
        cable["VERILOG.InlineConstraints"] = properties

    def parse_instantiation(self, properties):
        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "module identifier", "for instantiation", token
        )
        def_name = token.strip()

        parameter_dict = {}
        token = self.peek_token()
        if token == vt.OCTOTHORP:
            parameter_dict = self.parse_parameter_mapping()

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "instance name", "for instantiation", token
        )
        name = token.strip()

        # the current definition is instancing the current top instance, so a change needs to be made
        if def_name == self.netlist.top_instance.reference.name:
            # print(self.current_definition.name + " is instancing the current top instance (" + \
            # name+ " which is a "+ self.netlist.top_instance.reference.name+")")
            old_top_instance = self.netlist.top_instance

            new_level = self.current_definition
            # we know the current top is not right. So now we can move it up a level.
            # But double check to make sure nothing is instancing the potential new top.
            # Move up levels until we reach a new top
            if len(self.current_definition.references) > 0:
                current_level = list(x for x in self.current_definition.references)[0]
                while True:
                    current_level = current_level.parent
                    try:
                        current_level.parent
                    except AttributeError:
                        new_level = current_level
                        break

            self.netlist.top_instance = Instance()
            self.netlist.top_instance.name = new_level.name + "_top"
            self.netlist.top_instance.reference = new_level
            self.netlist.name = "SDN_VERILOG_NETLIST_" + new_level.name

            # print("New top instance is "+ self.netlist.top_instance.name)

            # this instance should just go away. It was created to be the top instance but we don't
            # want that it has no parent. And now with no reference, it should have no ties to the
            # netlist.
            old_top_instance.reference = None

        token = self.peek_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to start port to cable mapping", token
        )

        instance = self.current_definition.create_child()
        self.current_instance = instance

        instance.name = name
        instance.reference = self.blackbox_holder.get_blackbox(def_name)
        instance["VERILOG.InlineConstraints"] = properties

        self.parse_port_mapping()

        self.set_instance_parameters(instance, parameter_dict)

        token = self.next_token()
        assert token == vt.SEMI_COLON, self.error_string(
            vt.SEMI_COLON, "to end instatiation", token
        )

    def parse_defparam_parameters(self):
        """parse a defparam structure and add the parameters to the associated instance

        this looks like:

        defparam \\avs_s1_readdata[12]~output .bus_hold = "false"; //single backslash to escape
        name

        and must come after the associated instance (I'm not sure this is the verilog spec but it
        is the way quartus wrote my example and is much simpler)
        """
        params = {}
        token = self.next_token()
        assert token == vt.DEFPARAM, self.error_string(
            vt.DEFPARAM, "to being defparam statement", token
        )
        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "valid identifier", "of an instance to apply the defparam to", token
        )
        instance_name = token.strip()
        if self.current_instance.name == instance_name:
            instance = self.current_instance
        else:
            instance = next(self.current_definition.get_instances(instance_name), None)
            assert instance is not None, self.error_string(
                "identifer of existing instance",
                "within the current definition",
                instance_name,
            )
        token = self.next_token()
        assert token == vt.DOT, self.error_string(
            vt.DOT, "give separate parameter key from the instance name", token
        )
        token = self.next_token()
        key = token
        token = self.next_token()
        assert token == vt.EQUAL, self.error_string(
            vt.EQUAL, "separate the key from the value in a defparam statement", token
        )
        token = self.next_token()
        value = token
        params[key] = value
        token = self.next_token()
        assert token == vt.SEMI_COLON, self.error_string(
            vt.SEMI_COLON, "to end the defparam statement", token
        )
        self.set_instance_parameters(instance, params)

    def parse_parameter_mapping(self):
        params = {}
        token = self.next_token()
        assert token == vt.OCTOTHORP, self.error_string(
            vt.OCTOTHORP, "to begin parameter mapping", token
        )

        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "after # to begin parameter mapping", token
        )

        if self.peek_token() == vt.CLOSE_PARENTHESIS:  # empty parameters
            token = self.next_token()
        else:
            while token != vt.CLOSE_PARENTHESIS:
                k, v = self.parse_parameter_map_single()
                params[k] = v
                token = self.next_token()
                assert token in [vt.CLOSE_PARENTHESIS, vt.COMMA], self.error_string(
                    vt.COMMA + " or " + vt.CLOSE_PARENTHESIS,
                    "to separate parameters or end parameter mapping",
                    token,
                )

        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "to terminate ", token
        )

        return params

    def parse_parameter_map_single(self):
        # syntax looks like .identifier(value)
        token = self.next_token()
        assert token == vt.DOT, self.error_string(
            vt.DOT, "to begin parameter mapping", token
        )

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "valid parameter identifier", "in parameter mapping", token
        )
        k = token.strip()

        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "after identifier in parameter mapping", token
        )

        token = self.next_token()
        v = token

        token = self.next_token()
        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "to close the parameter mapping value", token
        )

        return k, v

    def parse_port_mapping(self):
        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to start the port mapping", token
        )

        peeked_token = self.peek_token()
        if peeked_token != vt.DOT:  # the ports are implicitly mapped
            token_list = []
            while token != vt.CLOSE_PARENTHESIS:
                token_list.append(token)
                token = self.next_token()
            token_list.append(token)
            self.implicitly_mapped_ports[self.current_instance] = token_list
        else:  # the ports are explicitly mapped
            while token != vt.CLOSE_PARENTHESIS:
                self.parse_port_map_single()
                token = self.next_token()
        assert token in [vt.COMMA, vt.CLOSE_PARENTHESIS], self.error_string(
            vt.COMMA + " or " + vt.CLOSE_PARENTHESIS,
            "between port mapping elements or to end the port mapping",
            token,
        )

    def parse_port_map_single(self):
        """acutally does the mapping of the pins"""
        token = self.next_token()
        assert token == vt.DOT, self.error_string(
            vt.DOT, "to start a port mapping instance", token
        )

        token = self.next_token()
        assert vt.is_valid_identifier(token), self.error_string(
            "valid port identifier", "for port in instantiation port map", token
        )
        port_name = token.strip()

        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to encapsulate cable name in port mapping", token
        )

        token = self.peek_token()

        is_downto = True
        if token != vt.CLOSE_PARENTHESIS:
            if token == vt.OPEN_BRACE:
                wires = self.parse_cable_concatenation()
            else:
                cable_lr_list = self.parse_variable_instantiation()
                assert len(cable_lr_list) == 1, self.error_string(
                    'one entity declaration', "port mapping", token
                )
                cable, left, right = cable_lr_list[0]
                wires = self.get_wires_from_cable(cable, left, right)
                is_downto = cable.is_downto

            pins = self.create_or_update_port_on_instance(
                port_name, len(wires), is_downto
            )

            assert len(pins) >= len(wires), self.error_string(
                "pins length to match or exceed cable.wires length",
                "INTERNAL ERROR",
                str(len(pins)) + "!=" + str(len(wires)),
            )

            # there can be unconnected pins at the end of the port.
            pins.sort(reverse=True, key=self.pin_sort_func)
            # the offset makes sure connections are on lower
            # end of the port for partially connected ports
            offset = 0
            if len(pins) > len(wires):
                offset = len(pins) - len(wires)
            for i in range(len(wires)):
                wires[i].connect_pin(pins[offset + i])

            token = self.next_token()

        else:
            # consume the )
            token = self.next_token()
            # the port is intentionally left unconnected.
            self.create_or_update_port_on_instance(port_name, 1)

        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "to end cable name in port mapping", token
        )

    def pin_sort_func(self, p):
        if isinstance(p, OuterPin):
            return p.inner_pin.port.pins.index(p.inner_pin)
        return p.port.pins.index(p)

    def connect_implicitly_mapped_ports(self):
        for instance, token_list in self.implicitly_mapped_ports.items():
            self.current_instance = instance
            self.current_definition = instance.parent
            port_list = list(x for x in instance.reference.get_ports())
            self.tokenizer = VerilogTokenizerSimple(token_list)

            token = self.next_token()
            assert token == vt.OPEN_PARENTHESIS, self.error_string(
                vt.OPEN_PARENTHESIS, "to encapsulate cable name in port mapping", token
            )

            index = 0

            # There may be no mapped wires at all. It may be empty or filled with whitespace
            token = self.peek_token()

            if token == vt.CLOSE_PARENTHESIS:
                # Consume the token, we're going to skip the loop
                token = self.next_token()

            while token != vt.CLOSE_PARENTHESIS:
                token = self.peek_token()

                if token == vt.OPEN_BRACE:
                    wires = self.parse_cable_concatenation()
                else:
                    cable_lr_list = self.parse_variable_instantiation()
                    assert len(cable_lr_list) == 1, self.error_string(
                        'one entity declaration', "port mapping", token
                    )
                    cable, left, right = cable_lr_list[0]
                    wires = self.get_wires_from_cable(cable, left, right)

                if (
                    index > len(port_list) - 1
                ):  # no port exists yet i.e. no module information in netlist
                    # print("Not enough ports for "+ instance.name)
                    port = instance.reference.create_port()
                    self.populate_new_port(port, None, len(wires) - 1, 0, None)
                else:
                    port = port_list[index]

                pins = []
                for pin in self.current_instance.pins:
                    if pin.inner_pin in port.pins:
                        pins.append(pin)

                assert len(pins) >= len(wires), self.error_string(
                    "pins length to match or exceed cable.wires length",
                    "INTERNAL ERROR",
                    str(len(pins)) + "!=" + str(len(wires)),
                )

                # there can be unconnected pins at the end of the port.
                pin_list = list(p for p in pins)
                pin_list.sort(reverse=True, key=self.pin_sort_func)
                # the offset makes sure connections are on lower
                # end of the port for partially connected ports
                offset = 0
                if len(pin_list) > len(wires):
                    offset = len(pin_list) - len(wires)
                for i in range(len(wires)):
                    wires[i].connect_pin(pin_list[offset + i])

                token = self.next_token()
                index += 1

            assert token == vt.CLOSE_PARENTHESIS, self.error_string(
                vt.CLOSE_PARENTHESIS, "to end cable name in port mapping", token
            )

    def parse_assign(self):
        token = self.next_token()
        assert token == vt.ASSIGN, self.error_string(
            vt.ASSIGN, "to begin assignment statement", token
        )
        # separating lhs into single bits
        lhs_cables_list = self.parse_assign_side_cables()
        token = self.next_token()
        assert token == vt.EQUAL, self.error_string(
            vt.EQUAL, "in assigment statment", token
        )

        # separating rhs into single bits
        rhs_cables_list = self.parse_assign_side_cables()

        token = self.next_token()
        assert token == vt.SEMI_COLON, self.error_string(
            vt.SEMI_COLON, "to terminate assign statement", token
        )

        # matching cable entries from two lists to create
        # several single-bit assignments
        assert len(lhs_cables_list) == len(rhs_cables_list), self.error_string(
            "lhs and rhs of similar size", "in assign statement", token)

        result_cables_list = []
        for idx in range(0, len(lhs_cables_list)):
            lhs_tuple = lhs_cables_list[idx]
            rhs_tuple = rhs_cables_list[idx]

            result_cables_list.append((
                lhs_tuple[0], lhs_tuple[1], lhs_tuple[2],
                rhs_tuple[0], rhs_tuple[1], rhs_tuple[2]))

        return result_cables_list

    def parse_assign_side_cables(self):
        # separating left hand-side if it is a bundle
        raw_cables_list = []
        peek_next = self.peek_token()
        if peek_next == vt.OPEN_BRACE:
            token = self.next_token()
            while(token != vt.CLOSE_BRACE):
                cable_lr_list = self.parse_variable_instantiation()
                raw_cables_list.extend(cable_lr_list)
                token = self.next_token()
        else:
            cable_lr_list = self.parse_variable_instantiation()
            raw_cables_list.extend(cable_lr_list)

        # separating into single bits
        cables_list = []
        for (cable, left, right) in raw_cables_list:
            if left != None and right == None:
                cables_list.append((cable, left, right))
                continue
            elif left == None or right == None:
                if len(cable.wires) == 1:
                    cables_list.append((cable, left, right))
                    continue
                else:
                    # decomposing bus into bits
                    left = cable.lower_index
                    right = left + len(cable.wires) - 1
                    if cable.is_downto:
                        left, right = right, left

            incr = 1 if left < right else -1
            for idx in range(left, right+incr, incr):
                cables_list.append((cable, idx, None))

        return cables_list

    def parse_variable_instantiation(self):
        """parse the cable name and its indicies if any
        if we are in Intel land then 2 other things can happen.
        the "cable" is a constant,
            attach it to the \\<const0> or \\<const1> cable.
        the cable is inverted,
            create a new cable and an inverter block similar to the assign but with an inversion in the block
        """
        token = self.next_token()

        names_list = []

        if re.match("[0-9]+'", token):
            quote_pos = token.index('\'')
            bits_num = int(token[0:quote_pos])
            bdh_char = token[quote_pos + 1]

            bits_entry = token[quote_pos + 2:]
            bits_list = []

            # need to preserve order as it is to match the other side of expression
            if bdh_char == 'b':
                bits_list = list(bits_entry[::1])
            elif bdh_char == 'd':
                bin_data = bin(int(bits_entry))[2:]
                bits_list = list(bin_data[::1])
            elif bdh_char == 'h':
                bin_data = bin(int(bits_entry, 16))[2:]
                bits_list = list(bin_data[::1])
            else:
                assert False, self.error_string('bdh', "in the constant", token)

            assert len(bits_list) == bits_num, self.error_string(
                len(bits_list), "in size of the constant", token
            )

            for bit in bits_list:
                name = "\\<const" + bit + "> "
                names_list.append(name)
        else:
            names_list.append(token)

        result_cables_list = []

        # processing each name entry
        for name in names_list:
            assert vt.is_valid_identifier(name), self.error_string(
                "valid port identifier", "for port in instantiation port map", name
            )
            token = self.peek_token()
            left = None
            right = None
            if token == vt.OPEN_BRACKET:
                left, right = self.parse_brackets()

            cable = self.create_or_update_cable(
                name.strip(), left_index=left, right_index=right)

            result_cables_list.append((cable, left, right))

        return result_cables_list

    def parse_brackets(self):
        """returns 2 integer values or 1 integer value and none"""
        token = self.next_token()
        assert token == vt.OPEN_BRACKET, self.error_string(
            "[", "to begin array slice", token
        )
        token = self.next_token()
        assert self.is_numeric(token), self.error_string("number", "after [", token)
        left = int(token)
        token = self.next_token()
        if token == "]":
            return left, None
        else:
            assert token == vt.COLON, self.error_string(
                "] or :", "in array slice", token
            )
            token = self.next_token()
            assert self.is_numeric(token), self.error_string(
                "number", "after : in array slice", token
            )
            right = int(token)
            token = self.next_token()
            assert token == vt.CLOSE_BRACKET, self.error_string(
                "]", "to terminate array slice", token
            )
            return left, right

    def parse_star_property(self):
        token = self.next_token()
        assert token == vt.OPEN_PARENTHESIS, self.error_string(
            vt.OPEN_PARENTHESIS, "to begin star property", token
        )
        token = self.next_token()
        assert token == vt.STAR, self.error_string(
            vt.STAR, "to begin star property", token
        )
        properties_dict = {}
        token = self.next_token()
        while token != vt.STAR:
            assert vt.is_valid_identifier(token)
            key = token.strip()
            token = self.next_token()
            assert token in [vt.EQUAL, vt.STAR, vt.COMMA], self.error_string(
                vt.EQUAL + " or " + vt.STAR + " or " + vt.COMMA,
                "to set a star parameter",
                token,
            )
            if token == vt.EQUAL:
                token = self.next_token()
                value = ""
                while token != vt.STAR and token != vt.COMMA:
                    value += token
                    token = self.next_token()
            else:
                value = None
            properties_dict[key] = value
            if token != vt.STAR:
                token = self.next_token()
        assert token == vt.STAR, self.error_string(
            vt.STAR, "to start the ending of a star property", token
        )
        token = self.next_token()
        assert token == vt.CLOSE_PARENTHESIS, self.error_string(
            vt.CLOSE_PARENTHESIS, "to end the star property", token
        )

        return properties_dict

    #######################################################
    # assignment helpers
    #######################################################

    def get_assignment_library(self):
        """create or return a previously created assignment library"""
        if self.assigns is None:
            self.assigns = self.netlist.create_library(name="SDN_VERILOG_ASSIGNMENT")

        return self.assigns

    def get_assignment_definition(self, width):
        """get the definition of the specified width for assignments"""
        proposed_name = "SDN_VERILOG_ASSIGNMENT_" + str(width)
        library = self.get_assignment_library()
        definition = next(library.get_definitions(proposed_name), None)
        if definition is None:
            definition = library.create_definition(name=proposed_name)
            in_port = definition.create_port("i")
            out_port = definition.create_port("o")

            in_port.create_pins(width)
            out_port.create_pins(width)
            in_port.direction = sdn.Port.Direction.IN
            out_port.direction = sdn.Port.Direction.OUT

            # no need for this. It actually messes with other spydrnet functions like uniquify() and
            # is_leaf()
            # cable = definition.create_cable("through")
            # cable.create_wires(width)
            # for i in range(width):
            #     cable.wires[i].connect_pin(in_port.pins[i])
            #     cable.wires[i].connect_pin(out_port.pins[i])

        return definition

    def create_assignment_instance(self, width):
        """create a new assign instance of the specified width on the current definition"""
        definition = self.get_assignment_definition(width)
        instance_name = definition.name + "_" + str(self.assignment_count)
        self.assignment_count += 1
        instance = self.current_definition.create_child(instance_name)
        instance.reference = definition
        return instance

    def connect_wires_for_assign(
        self, l_cable, l_left, l_right, r_cable, r_left, r_right
    ):
        """connect the wires in r_left to the wires in l_left"""

        out_wires = self.get_wires_from_cable(l_cable, l_left, l_right)
        in_wires = self.get_wires_from_cable(r_cable, r_left, r_right)

        # min because we don't need extra pins since only what can will assign.
        width = min(len(out_wires), len(in_wires))
        instance = self.create_assignment_instance(width)

        in_port = next(instance.reference.get_ports("i"), None)
        out_port = next(instance.reference.get_ports("o"), None)

        in_pins = self.get_pins_by_port_from_instance(instance, in_port)
        out_pins = self.get_pins_by_port_from_instance(instance, out_port)

        for i in range(width):
            out_wires[i].connect_pin(out_pins[i])
            in_wires[i].connect_pin(in_pins[i])

    #######################################################
    # helper functions
    #######################################################

    def get_pins_by_port_from_instance(self, instance, port):
        pin_lookup = instance.pins
        pins_out = []
        for p in port.pins:
            pins_out.append(pin_lookup[p])
        return pins_out

    def set_instance_parameters(self, instance, params):
        for k, v in params.items():
            # self.set_single_parameter(instance.reference, k, None)
            self.set_single_parameter(instance, k, v)

    def set_definition_parameters(self, definition, params):
        for k, v in params.items():
            self.set_single_parameter(definition, k, v)

    def set_single_parameter(self, var, k, v):
        if "VERILOG.Parameters" not in var:
            var["VERILOG.Parameters"] = {}

        if k not in var["VERILOG.Parameters"] or var["VERILOG.Parameters"][k] is None:
            var["VERILOG.Parameters"][k] = v

    def get_all_ports_from_wires(self, wires):
        """gets all ports associated with a set of wires"""
        ports = set()
        for w in wires:
            for p in w.pins:
                if isinstance(p, sdn.InnerPin):
                    ports.add(p.port)
        return ports

    def get_wires_from_cable(self, cable, left, right):
        wires = []

        if left is not None and right is not None:
            left = left - cable.lower_index
            right = right - cable.lower_index
            temp_wires = cable.wires[min(left, right) : max(left, right) + 1]
            # if right > left:
            temp_wires.reverse()
            for w in temp_wires:
                wires.append(w)
            if not cable.is_downto:
                wires.reverse()
        elif left is not None or right is not None:
            if left is not None:
                index = left - cable.lower_index
            else:
                index = right - cable.lower_index
            wires.append(cable.wires[index])

        else:
            temp_wires = list(w for w in cable.wires)
            if cable.is_downto:
                temp_wires.reverse()
            for w in temp_wires:
                wires.append(w)

        return wires

    def convert_string_to_port_direction(self, token):
        if token == vt.INPUT:
            return sdn.Port.Direction.IN
        if token == vt.INOUT:
            return sdn.Port.Direction.INOUT
        if token == vt.OUTPUT:
            return sdn.Port.Direction.OUT
        else:
            return sdn.Port.Direction.UNDEFINED

    ########################################################################################
    # Port and cable creation and update managment
    ########################################################################################

    """I'm handed a few different possible senarios

    module name(port1, port2,...);
    input [3:0] port1
    output [3:0] port2
    endmodule

    or

    module name
    (
        input [3:0] port1,
        output[3:0] port2,
        ...
    );

    additionally i need to be aware of the possibility that something like this happens

    module name(.port1({cable1, cable2}));
    input [1:0] cable1;
    output [1:0] cable2;
    """

    def connect_resized_port_cable(self, resized_cable, resized_port):
        """
        One to one connector. Don't use with alias statements. this expects that the given cable
        should completely fill the port... after a cable has been updated that is attached to a port
        it may need to update the port and reconnect the
        """
        assert len(resized_cable.wires) == len(resized_port.pins), self.error_string(
            "cable and port to have same size",
            "to reconnect expanded cables and ports",
            "wires: "
            + str(len(resized_cable.wires))
            + " pins: "
            + str(len(resized_port.pins)),
        )
        for i in range(len(resized_port.pins)):
            # I think these should be lined up right?
            if resized_port.pins[i] not in resized_cable.wires[i].pins:
                if resized_port.pins[i].wire:
                    continue
                    # the resized_port's pin is already connected
                    # this likely occurred because of an alias statement.
                resized_cable.wires[i].connect_pin(resized_port.pins[i])

    def create_or_update_cable(
        self, name, left_index=None, right_index=None, var_type=None, defining=False
    ):
        cable_generator = self.current_definition.get_cables(name)
        cable = next(cable_generator, None)
        if cable is None:
            cable = self.current_definition.create_cable()
            self.populate_new_cable(cable, name, left_index, right_index, var_type)
            return cable

        assert cable.name == name

        cable_lower = cable.lower_index
        # -1 so that it is the same number if the width is 1
        cable_upper = cable.lower_index + len(cable.wires) - 1

        if left_index is not None and right_index is not None:
            in_lower = min(left_index, right_index)
            in_upper = max(left_index, right_index)
        elif left_index is not None:
            in_lower = left_index
            in_upper = left_index
        elif right_index is not None:
            in_upper = right_index
            in_lower = right_index
        else:
            in_upper = None
            in_lower = None

        if (
            defining and in_lower is not None
        ):  # if the cable width is being defined then recenter the cable
            cable.lower_index = in_lower
            cable_lower = cable.lower_index
            cable_upper = cable.lower_index + len(cable.wires) - 1
            cable.is_downto = right_index <= left_index

        if in_upper is not None and in_lower is not None:
            if in_lower < cable_lower:
                prepend = cable_lower - in_lower
                self.prepend_wires(cable, prepend)
            if in_upper > cable_upper:
                postpend = in_upper - cable_upper
                self.postpend_wires(cable, postpend)

        if var_type is not None:
            cable["VERILOG.CableType"] = var_type

        return cable

    def populate_new_cable(self, cable, name, left_index, right_index, var_type):
        cable.name = name
        if left_index is not None and right_index is not None:
            cable.is_downto = right_index <= left_index
            cable.create_wires(
                max(left_index, right_index) - min(left_index, right_index) + 1
            )
            cable.lower_index = min(left_index, right_index)
        elif left_index is not None:
            cable.lower_index = left_index
            cable.create_wire()
        elif right_index is not None:
            cable.lower_index = right_index
            cable.create_wire()
        else:
            cable.lower_index = 0
            cable.create_wire()

        if var_type:
            cable["VERILOG.CableType"] = var_type

        return cable

    def prepend_wires(self, cable, count):
        orig_count = len(cable.wires)
        cable.create_wires(count)
        cable.wires = cable.wires[orig_count:] + cable.wires[:orig_count]
        cable.lower_index = cable.lower_index - count

    def postpend_wires(self, cable, count):
        cable.create_wires(count)

    def create_or_update_port_on_instance(self, name, width, is_downto=True):
        """returns the set of pins associated with the port on the instance"""
        pins = []
        port = self.create_or_update_port(
            name,
            left_index=(width - 1) if is_downto else 0,
            right_index=0 if is_downto else (width - 1),
            definition=self.current_instance.reference,
        )
        for pin in self.current_instance.pins:
            if pin.inner_pin in port.pins:
                pins.append(pin)
        return pins

    def create_or_update_port(
        self,
        name,
        left_index=None,
        right_index=None,
        direction=None,
        definition=None,
        defining=False,
    ):
        if definition is None:
            definition = self.current_definition

        port_generator = definition.get_ports(name)
        port = next(port_generator, None)
        if port is None:
            port = definition.create_port()
            self.populate_new_port(port, name, left_index, right_index, direction)
            return port

        assert port.name == name

        # figure out what we need to do with the indicies

        port_lower = port.lower_index
        # -1 so that it is the same number if the width is 1
        port_upper = port.lower_index + len(port.pins) - 1

        if left_index is not None and right_index is not None:
            in_lower = min(left_index, right_index)
            in_upper = max(left_index, right_index)
        elif left_index is not None:
            in_lower = left_index
            in_upper = left_index
        elif right_index is not None:
            in_upper = right_index
            in_lower = right_index
        else:
            in_upper = None
            in_lower = None

        if (
            defining and in_lower is not None
        ):  # if the cable width is being defined then recenter the cable
            port.lower_index = in_lower
            port_lower = port.lower_index
            port_upper = port.lower_index + len(port.pins) - 1
            port.is_downto = right_index <= left_index

        if in_upper is not None and in_lower is not None:
            # to prevent unneccessary pins being added, check to see if port
            # width is already correct
            if (in_upper - in_lower) == (port_upper - port_lower):
                None
            else:
                if in_lower < port_lower:
                    prepend = port_lower - in_lower
                    self.prepend_pins(port, prepend)
                if in_upper > port_upper:
                    postpend = in_upper - port_upper
                    self.postpend_pins(port, postpend)

        if direction is not None:
            port.direction = direction

        return port

    def populate_new_port(self, port, name, left_index, right_index, direction):
        port.name = name
        if left_index is not None and right_index is not None:
            port.is_downto = right_index <= left_index
            port.create_pins(
                max(left_index, right_index) - min(left_index, right_index) + 1
            )
            port.lower_index = min(left_index, right_index)
        elif left_index is not None:
            port.lower_index = left_index
            port.create_pin()
        elif right_index is not None:
            port.lower_index = right_index
            port.create_pin()
        else:
            port.lower_index = 0
            port.create_pin()

        if direction is not None:
            port.direction = direction

        return port

    def prepend_pins(self, port, count):
        orig_count = len(port.pins)
        port.create_pins(count)
        port.pins = port.pins[orig_count:] + port.pins[:orig_count]
        port.lower_index = port.lower_index - count

    def postpend_pins(self, port, count):
        port.create_pins(count)

    def is_numeric(self, token):
        first = True
        for c in token:
            if first:
                first = False
                if c == "-":
                    continue
            if c not in vt.NUMBERS:
                return False
        return True

    def is_alphanumeric(self, token):
        for c in token:
            if c not in vt.NUMBERS and c not in vt.LETTERS:
                return False
        return True

    def error_string(self, expected, why, result):
        """put in the expectation and then the reason or location and the actual result"""
        return (
            "expected "
            + str(expected)
            + " "
            + why
            + " but got "
            + str(result)
            + " Line: "
            + str(self.tokenizer.line_number)
        )
