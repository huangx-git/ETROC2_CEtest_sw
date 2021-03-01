
from module_test_sw.KCU import KCU
from module_test_sw.ReadoutBoard import ReadoutBoard
from module_test_sw.LPGBT import LPGBT

if __name__ == '__main__':

    kcu = KCU(name="my_device", ipb_path="ipbusudp-2.0://192.168.0.10:50001", adr_table="address_table/etl_test_fw.xml")

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=False))

    rb_0.configure()
