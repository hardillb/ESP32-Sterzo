import time
import struct
import bluetooth 
from micropython import const
from ble_advertising import advertising_payload


_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_INDICATE_DONE = const(20)



_SERVICE_UUID = bluetooth.UUID('347b0001-7635-408b-8918-8ff3949ce592')
_CHAR1_UUID = (bluetooth.UUID('347b0012-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_WRITE,)
_CHAR2_UUID = (bluetooth.UUID('347b0013-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_READ,)
_CHAR3_UUID = (bluetooth.UUID('347b0014-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_NOTIFY,)
_CHAR4_UUID = (bluetooth.UUID('347b0019-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_READ,)

_RXCHAR_UUID = (bluetooth.UUID('347b0031-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_WRITE,)
_TXCHAR_UUID = (bluetooth.UUID('347b0032-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_READ|bluetooth.FLAG_INDICATE,)

_STEERING_UUID = (bluetooth.UUID('347b0030-7635-408b-8918-8ff3949ce592'), bluetooth.FLAG_READ|bluetooth.FLAG_NOTIFY,)

_SERVICE = (_SERVICE_UUID, (_CHAR1_UUID, _CHAR2_UUID, _CHAR3_UUID, _CHAR4_UUID, _RXCHAR_UUID, _TXCHAR_UUID, _STEERING_UUID),)

class Steerer:
	def __init__(self, ble, name='steerer'):
		self._ble = ble
		self._ble.active(True)
		self._ble.irq(self._irq)

		self._enabled = False

		((self._handle_char1, self._handle_char2, self._handle_char3, 
			self._handle_char4, self._handle_rx, self._handle_tx, self._handle_steer),) = self._ble.gatts_register_services((_SERVICE,))

		self._connections = set()
		self._payload = advertising_payload(name=name, services=[_SERVICE_UUID])
		self._advertise()


	def _irq(self, event, data):
		# Track connections so we can send notifications.
		if event == _IRQ_CENTRAL_CONNECT:
			conn_handle, _, _, = data
			self._connections.add(conn_handle)
		elif event == _IRQ_CENTRAL_DISCONNECT:
			conn_handle, _, _, = data
			self._connections.remove(conn_handle)
			# Start advertising again to allow a new connection.
			self._advertise()
			self._enabled = False
		elif event == _IRQ_GATTS_INDICATE_DONE:
			conn_handle, value_handle, status = data
		elif event == _IRQ_GATTS_WRITE:
			conn_handle, value_handle = data
			if conn_handle in self._connections and value_handle == self._handle_rx:
				value = self._ble.gatts_read(value_handle)
				print("write {}".format(value))
				(val,) = struct.unpack(">h", value)
				print("write {}".format(val))
				if val == 0x0310:
					print("first")
					resp = struct.pack('>hh',0x0310, 0x4a89)
					self._ble.gatts_write(self._handle_tx,resp)
					self._ble.gatts_indicate(conn_handle, self._handle_tx)
				elif val == 0x0311:
					print("second")
					resp = struct.pack('>hh',0x0311, 0xffff)
					self._ble.gatts_write(self._handle_tx,resp)
					self._ble.gatts_indicate(conn_handle, self._handle_tx)
					self._enabled = True
				elif val == 0x0202:
					print("Received 0x0202")
				else:
					print("no match")

	def update(self, angle):
		steering_data = struct.pack('<f', angle)
		self._ble.gatts_write(self._handle_steer, steering_data)

		for conn_handle in self._connections:
			if self._enabled:
				self._ble.gatts_notify(conn_handle, self._handle_steer)

	def _advertise(self, interval_us=500000):
		self._ble.gap_advertise(interval_us, adv_data=self._payload)

def start():
	print("Zwift Sterring test\n")
	## BLUETOOTH
	ble = bluetooth.BLE()
	ble_module = Steerer(ble)

	angle = -15
	modifier = 1

	print("starting\n")

	while True:

		print("loop {}".format(angle))

		ble_module.update(angle)
		angle = angle + modifier

		if angle == 15:
			modifier = -1
		elif angle == -15:
			modifier = 1

		time.sleep(1)

start()