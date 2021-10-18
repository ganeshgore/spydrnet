import unittest

import spydrnet as sdn
from spydrnet.ir.cable import Cable
from spydrnet.ir.definition import Definition
from spydrnet.ir.first_class_element import FirstClassElement
from spydrnet.ir.port import Port


class TestDefinition(unittest.TestCase):
    def setUp(self):
        self.definition = sdn.Definition()

    def test_constructor(self):
        self.assertIsInstance(self.definition, FirstClassElement, "Definition is not an element.")
        self.assertTrue(self.definition, "Constructor returns None type or empty collection.")
        definition2 = sdn.Definition()
        self.assertNotEqual(self.definition, definition2, "Unique objects are considered equal.")

    @unittest.expectedFailure
    def test_assign_library(self):
        library = sdn.Library()
        self.definition.library = library

    def test_ports_set(self):
        port1 = self.definition.create_port()
        port2 = self.definition.create_port()
        self.assertEqual(self.definition.ports, [port1, port2])
        self.definition.ports = [port2, port1]
        self.assertEqual(self.definition.ports, [port2, port1])

    def test_create_port(self):
        port = self.definition.create_port()
        self.assertTrue(port in self.definition.ports)
        self.assertEqual(port.definition, self.definition)

    def test_add_port(self):
        port = sdn.Port()
        self.definition.add_port(port, position=0)
        self.assertTrue(port in self.definition.ports)
        self.assertEqual(port.definition, self.definition)
        self.assertEqual(self.definition.ports.count(port), 1)

    def test_remove_port(self):
        port = self.definition.create_port()
        self.definition.remove_port(port)
        self.assertFalse(port in self.definition.ports)
        self.assertIsNone(port.definition)

    def test_disconnect_port(self):
        """Checks if remove port clears the connected inner pin
        """
        port = self.definition.create_port()
        cable = self.definition.create_cable()
        p1 = port.create_pin()
        w1 = cable.create_wire()
        w1.connect_pin(p1)
        self.definition.disconnect_port(port)
        self.assertTrue(w1.pins == [])
        self.assertTrue(p1 in port.pins)

    @unittest.expectedFailure
    def test_remove_ports_from_outside_definition(self):
        port = sdn.Port()
        self.definition.remove_ports_from((port,))

    def test_remove_ports_from(self):
        port_included = self.definition.create_port()
        port = self.definition.create_port()
        self.definition.remove_ports_from((port,))
        self.assertFalse(port in self.definition.ports)
        self.assertIsNone(port.definition)

        port = self.definition.create_port()
        self.definition.remove_ports_from({port})
        self.assertFalse(port in self.definition.ports)
        self.assertIsNone(port.definition)

        self.assertTrue(port_included in self.definition.ports)
        self.assertEqual(port_included.definition, self.definition)

    def test_cables_set(self):
        cable1 = self.definition.create_cable()
        cable2 = self.definition.create_cable()
        self.assertEqual(self.definition.cables, [cable1, cable2])
        self.definition.cables = [cable2, cable1]
        self.assertEqual(self.definition.cables, [cable2, cable1])

    def test_create_cable(self):
        cable = self.definition.create_cable()
        self.assertTrue(cable in self.definition.cables)
        self.assertEqual(self.definition, cable.definition)

    def test_add_cable(self):
        cable = sdn.Cable()
        self.definition.add_cable(cable, position=0)
        self.assertTrue(cable in self.definition.cables)
        self.assertEqual(cable.definition, self.definition)
        self.assertEqual(self.definition.cables.count(cable), 1)

    def test_remove_cable(self):
        cable = self.definition.create_cable()
        self.definition.remove_cable(cable)
        self.assertFalse(cable in self.definition.cables)
        self.assertIsNone(cable.definition)

    @unittest.expectedFailure
    def test_remove_cables_from_outside_definition(self):
        cable = sdn.Cable()
        self.definition.remove_cables_from({cable})

    def test_remove_cables_from(self):
        cable_included = self.definition.create_cable()
        cable = self.definition.create_cable()
        self.definition.remove_cables_from({cable})
        self.assertFalse(cable in self.definition.cables)
        self.assertIsNone(cable.definition)
        self.assertTrue(cable_included in self.definition.cables)
        self.assertEqual(cable_included.definition, self.definition)

    def test_children_set(self):
        child1 = self.definition.create_child()
        child2 = self.definition.create_child()
        self.assertEqual(self.definition.children, [child1, child2])
        self.definition.children = [child2, child1]
        self.assertEqual(self.definition.children, [child2, child1])

    def test_create_child(self):
        instance = self.definition.create_child()
        self.assertTrue(instance in self.definition.children)
        self.assertEqual(instance.parent, self.definition)

    def test_add_child(self):
        instance = sdn.Instance()
        self.definition.add_child(instance, position=0)
        self.assertTrue(instance in self.definition.children)
        self.assertEqual(instance.parent, self.definition)
        self.assertEqual(self.definition.children.count(instance), 1)

    def test_remove_child(self):
        instance = self.definition.create_child()
        self.definition.remove_child(instance)
        self.assertFalse(instance in self.definition.children)
        self.assertIsNone(instance.parent)

    @unittest.expectedFailure
    def test_remove_children_from_outside_definition(self):
        instance = sdn.Instance()
        self.definition.remove_children_from((instance,))

    def test_remove_children_from(self):
        instance_included = self.definition.create_child()

        instance = self.definition.create_child()
        self.definition.remove_children_from((instance,))
        self.assertFalse(instance in self.definition.children)
        self.assertIsNone(instance.parent)

        instance = self.definition.create_child()
        self.definition.remove_children_from({instance})
        self.assertFalse(instance in self.definition.children)
        self.assertIsNone(instance.parent)

        self.assertTrue(instance_included in self.definition.children)
        self.assertEqual(instance_included.parent, self.definition)

    def test_is_leaf(self):
        self.assertTrue(self.definition.is_leaf(), \
            "Empty definition is not considered a leaf cell")
        self.definition.create_port()
        self.assertTrue(self.definition.is_leaf(), \
            "Empty definition with a port is not considered a leaf cell")
        self.definition.create_cable()
        self.assertFalse(self.definition.is_leaf(), \
            "Definition with a cable is considered a leaf cell")
        self.definition.remove_cables_from(self.definition.cables)
        self.definition.create_child()
        self.assertFalse(self.definition.is_leaf(), \
            "Definition with a child instance is considered a leaf cell")
        self.definition.create_cable()
        self.assertFalse(self.definition.is_leaf(), \
            "Definition with a cable and child instance is considered a leaf cell")

    @unittest.expectedFailure
    def test_combine_ports(self):
        assert False

    def test_combine_cables(self):
        cable1 = self.definition.create_cable("cable1", wires=2)
        cable2 = self.definition.create_cable("cable2", wires=3)
        cable3 = self.definition.create_cable("cable3", wires=2)
        new_c = self.definition.combine_cables("m_cable", [cable1, cable2, cable3])
        self.assertTrue(
            set(new_c.wires).difference(cable1, cable2, cable3), \
                "Failed to merge wires")
        self.assertIsNone(
            self.definition.combine_cables("m_cable", [], quiet=True), \
                "quiet option not supressing error")

    def test_create_feedthroughs_ports(self):
        cable = sdn.Cable("cable1")
        cable.create_wires(4)
        port1, port2 =self.definition.create_feedthroughs_ports(cable, suffix="feed")
        self.assertIsInstance(port1, Port)
        self.assertIsInstance(port2, Port)
        self.assertFalse(set(port1.inner_wires).difference(port2.inner_wires))
        self.assertSetEqual(set(sdn.get_names(self.definition.ports)),
                            {"cable1_feed_in", "cable1_feed_out"})


    def test_create_feedthrough(self):
        module1 = Definition("module1")
        module2 = Definition("module2")
        driver_port = module1.create_port("driver_port", direction=sdn.OUT)
        load_port = module1.create_port("load_port", direction=sdn.IN)
        driver_port.create_pins(4)
        load_port.create_pins(4)
        inst0 = self.definition.create_child("inst0", reference=module1)
        inst1 = self.definition.create_child("inst1", reference=module1)
        ft_inst = self.definition.create_child("ft_inst", reference=module2)

        cable = self.definition.create_cable("cable")
        cable.create_wires(4)

        cable.connect_instance_port(inst0, driver_port)
        cable.connect_instance_port(inst1, load_port)

        newCables = self.definition.create_feedthrough(ft_inst, cable)

        # Check correctness of connections
        self.assertTrue(isinstance(newCables, Cable), \
                "Return value should be cable")
        self.assertEqual(newCables.size, 4, \
                "New cable should have same dimensions")
        self.assertSetEqual(set(map(lambda p: p.name, module2.ports)),
                        {"cable_ft_out", "cable_ft_in"})
        self.assertSetEqual(set(map(lambda p: p.name, self.definition.get_cables())),
                        {"cable", "cable_ft_in_0"})
        self.assertSetEqual(set(('cable_ft_in_0', 'cable')),
            set(sdn.get_names(ft_inst.get_cables(selection="OUTSIDE"))),
            "Checks if both the cable are connected to feedthoguh instance")
        self.assertSetEqual(set(('cable',)),
            set(sdn.get_names(inst0.get_cables(selection="OUTSIDE"))),
            "Checks if original wire name is still same ")
        self.assertSetEqual(set(('cable_ft_in_0',)),
            set(sdn.get_names(inst1.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")

    def test_create_feedthrough_multiple(self):
        module1 = Definition("module1")
        module2 = Definition("module2")
        driver_port = module1.create_port("driver_port", direction=Port.Direction.OUT)
        load_port = module1.create_port("load_port", direction=Port.Direction.IN)
        driver_port.create_pins(4)
        load_port.create_pins(4)

        inst0 = self.definition.create_child("inst0", reference=module1)
        inst1 = self.definition.create_child("inst1", reference=module1)
        inst2 = self.definition.create_child("inst2", reference=module1)
        inst3 = self.definition.create_child("inst3", reference=module1)

        ft_inst1 = self.definition.create_child("ft_inst1", reference=module2)
        ft_inst2 = self.definition.create_child("ft_inst2", reference=module2)

        cable1 = self.definition.create_cable("cable1")
        cable1.create_wires(4)
        cable2 = self.definition.create_cable("cable2")
        cable2.create_wires(4)

        cable1.connect_instance_port(inst0, driver_port)
        cable1.connect_instance_port(inst1, load_port)
        cable2.connect_instance_port(inst2, driver_port)
        cable2.connect_instance_port(inst3, load_port)

        mapping = ((cable1, (ft_inst1,)), (cable2, (ft_inst2,)))
        new_cables = self.definition.create_feedthrough_multiple(mapping)


        self.assertEqual(new_cables[0].size, 4, \
                "New cable should have same dimensions")
        self.assertEqual(new_cables[1].size, 4, \
                "New cable should have same dimensions")

        self.assertSetEqual(set(('cable1', 'cable1_ft_in_0')),
            set(sdn.get_names(ft_inst1.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2', 'cable2_ft_in_0')),
            set(sdn.get_names(ft_inst2.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")

        self.assertSetEqual(set(('cable1',)),
            set(sdn.get_names(inst0.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable1_ft_in_0',)),
            set(sdn.get_names(inst1.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2',)),
            set(sdn.get_names(inst2.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2_ft_in_0',)),
            set(sdn.get_names(inst3.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")

    def test_create_feedthrough_multiple_2(self):
        ''' Test feedthroughs from multiple groups of instances '''
        module1 = Definition("module1")
        module2 = Definition("module2")
        driver_port = module1.create_port("driver_port", direction=Port.Direction.OUT)
        load_port = module1.create_port("load_port", direction=Port.Direction.IN)
        driver_port.create_pins(4)
        load_port.create_pins(4)

        inst0 = self.definition.create_child("inst0", reference=module1)
        inst1 = self.definition.create_child("inst1", reference=module1)
        inst2 = self.definition.create_child("inst2", reference=module1)
        inst3 = self.definition.create_child("inst3", reference=module1)

        ft_inst1 = self.definition.create_child("ft_inst1", reference=module2)
        ft_inst2 = self.definition.create_child("ft_inst2", reference=module2)
        ft_inst11 = self.definition.create_child("ft_inst11", reference=module2)
        ft_inst22 = self.definition.create_child("ft_inst22", reference=module2)

        cable1 = self.definition.create_cable("cable1")
        cable1.create_wires(4)
        cable2 = self.definition.create_cable("cable2")
        cable2.create_wires(4)

        cable1.connect_instance_port(inst0, driver_port)
        cable1.connect_instance_port(inst1, load_port)
        cable2.connect_instance_port(inst2, driver_port)
        cable2.connect_instance_port(inst3, load_port)

        mapping = ((cable1, (ft_inst1, ft_inst11)),
                   (cable2, (ft_inst2, ft_inst22)))

        new_cables = self.definition.create_feedthrough_multiple(mapping)

        for cable in new_cables:
            self.assertIsInstance(cable, Cable, \
                "Return values in not cable")
            self.assertEqual(cable.size, 4, \
                "New cable should have same dimensions")

        self.assertSetEqual(set(('cable1', 'cable1_ft_1')),
            set(sdn.get_names(ft_inst1.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2', 'cable2_ft_1')),
            set(sdn.get_names(ft_inst2.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable1_ft_0', 'cable1_ft_1')),
            set(sdn.get_names(ft_inst11.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2_ft_0', 'cable2_ft_1')),
            set(sdn.get_names(ft_inst22.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")

        self.assertSetEqual(set(('cable1',)),
            set(sdn.get_names(inst0.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable1_ft_0',)),
            set(sdn.get_names(inst1.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2',)),
            set(sdn.get_names(inst2.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")
        self.assertSetEqual(set(('cable2_ft_0',)),
            set(sdn.get_names(inst3.get_cables(selection="OUTSIDE"))),
            "Checks if feethrough wire name is as expected ")

    def test_duplicate_port(self):
        pin = self.definition.create_port("pin", pins=4)
        pout = self.definition.create_port("pout", pins=4)
        pin.direction = pin.Direction.IN
        pout.direction = pout.Direction.OUT
        c1 = self.definition.create_cable("cable1", wires=4)
        c1.connect_port(pin)
        c1.connect_port(pout)
        pin2 = self.definition.duplicate_port(pin, "_duplicate")

        self.assertIsInstance(pin2, Port)
        self.assertIsNot(pin2, pin)
        self.assertEqual(pin2.size, pin.size)
        self.assertEqual(pin2.direction, pin.direction)
        self.assertTrue(False)
        # Need more test to check if its feedthrough correctly