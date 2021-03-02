import xml.etree.ElementTree as xml


class Node:
    name = ''
    vhdlname = ''
    address = 0x0
    real_address = 0x0
    permission = ''
    mask = 0x0
    lsb_pos = 0x0
    is_module = False
    parent = None
    level = 0
    mode = None

    def __init__(self, top_node_name):
        self.top_node_name = top_node_name
        self.children = []

    def addChild(self, child):
        self.children.append(child)

    def getVhdlName(self):
        return self.name.replace(self.top_node_name + '.', '').replace('.', '_')

    def output(self):
        print('Name:', self.name)
        print('Address:', '{0:#010x}'.format(self.address))
        print('Permission:', self.permission)
        print('Mask:', self.mask)
        print('LSB:', self.lsb_pos)
        print('Module:', self.is_module)
        print('Parent:', self.parent.name)


class RegParser(object):

    def __init__(self):
        self.nodes = []

        self.parse_xml()

    # Functions related to parsing registers.xml
    def parse_xml(self, address_table='../address_table/lpgbt.xml', top_node_name="LPGBT"):
        self.address_table = address_table
        self.top_node_name = top_node_name
        print('Parsing', address_table, '...')
        self.tree = xml.parse(address_table)
        root = self.tree.getroot()[0]
        self.vars = {}
        self.make_tree(root, '', 0x0, self.nodes, None, self.vars, False)

    def make_tree(self, node, base_name, base_address, nodes, parent_node, vars, is_generated):
        if ((is_generated is None or is_generated is False)
            and node.get('generate') is not None
                and node.get('generate') == 'true'):

            generate_size = self.parse_int(node.get('generate_size'))
            generate_step = self.parse_int(node.get('generate_address_step'))
            generate_var = node.get('generate_idx_var')
            for i in range(0, generate_size):
                vars[generate_var] = i
                self.make_tree(node, base_name, base_address + generate_step * i, nodes, parent_node, vars, True)
            return

        new_node = Node(self.top_node_name)
        name = base_name
        if base_name != '':
            name += '.'
        name += node.get('id')
        name = self.substitute_vars(name, vars)
        new_node.name = name
        address = base_address
        if node.get('address') is not None:
            address = base_address + self.parse_int(eval(node.get('address')))
        new_node.address = address
        new_node.real_address = address
        new_node.permission = node.get('permission')
        new_node.mask = self.parse_int(node.get('mask'))
        new_node.lsb_pos = self.mask_to_lsb(new_node.mask)
        new_node.is_module = node.get('fw_is_module') is not None and node.get('fw_is_module') == 'true'
        if node.get('mode') is not None:
            new_node.mode = node.get('mode')
        nodes.append(new_node)
        if parent_node is not None:
            parent_node.addChild(new_node)
            new_node.parent = parent_node
            new_node.level = parent_node.level+1
        for child in node:
            self.make_tree(child, name, address, self.nodes, new_node, vars, False)

    def dump(self, nMax=99999):
        for i, node in enumerate(self.nodes[:nMax]):
            if i > 0:
                print(node.name)

    def get_all_children(self, node, kids=[]):
        if node.children == []:
            kids.append(node)
            return kids
        else:
            for child in node.children:
                get_all_children(child, kids)

    def get_node(self, nodeName):
        thisnode = next(
            (node for node in self.nodes if node.name == nodeName), None
        )
        if thisnode is None:
            print(nodeName)
        return thisnode

    def get_node_by_id(self, number):
        return self.nodes[number]

    def get_node_from_address(self, nodeAddress):
        return next((node for node in self.nodes if node.real_address == nodeAddress), None)

    def get_nodes_containing(self, nodeString):
        nodelist = [node for node in self.nodes if nodeString in node.name]
        if len(nodelist):
            return nodelist
        else:
            return None

    def get_regs_containing(self, nodeString):
        nodelist = [node for node in self.nodes if
                    nodeString in node.name and node.permission is not None and 'r' in node.permission]
        if len(nodelist):
            return nodelist
        else:
            return None

    def read_reg(self, mpeek, reg):
        try:
            address = reg.real_address
        except:
            print('Reg', reg, 'not a Node')
            return

        if 'r' not in reg.permission:
            print('No read permission!')
            return 'No read permission!'

        # read
        value = mpeek(address)

        # Apply Mask
        if reg.mask != 0:
            value = (reg.mask & value) >> reg.lsb_pos

        return value

    def write_reg(self, mpoke, mpeek, reg, value, readback=False):
        try:
            address = reg.real_address
        except:
            print('Reg', reg, 'not a Node')
            return
        if 'w' not in reg.permission:
            return 'No write permission!'

        if readback:
            read = read_reg(mpeek, reg)
            if value != read:
                print("ERROR: Failed to read back register %s. Expect=0x%x Read=0x%x" % (reg.name, value, read))
        else:
            # Apply Mask if applicable
            if reg.mask != 0:
                value = value << reg.lsb_pos
                value = value & reg.mask
                if 'r' in reg.permission:
                    value = (value) | (mpeek(address) & ~reg.mask)
            # mpoke
            mpoke(address, value)

    def substitute_vars(self, string, vars):
        if string is None:
            return string
        ret = string
        for varKey in vars.keys():
            ret = ret.replace('${' + varKey + '}', str(vars[varKey]))
        return ret

    def mask_to_lsb(self, mask):
        if mask is None:
            return 0
        if (mask & 0x1):
            return 0
        else:
            idx = 1
            while (True):
                mask = mask >> 1
                if (mask & 0x1):
                    return idx
                idx = idx+1

    def parse_int(self, s):
        if s is None:
            return None
        string = str(s)
        if string.startswith('0x'):
            return int(string, 16)
        elif string.startswith('0b'):
            return int(string, 2)
        else:
            return int(string)


def main():

    lpgbt = RegParser()
    lpgbt.dump()


if __name__ == '__main__':
    main()
