
from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.LPGBT import LPGBT

if __name__ == '__main__':

    kcu = KCU(name="my_device", ipb_path="ipbusudp-2.0://192.168.0.10:50001", adr_table="address_table/etl_test_fw.xml")
    kcu.status()

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=False))

    rb_0.configure()
    rb_0.DAQ_LPGBT.status()
