import ctypes
#Build jsinterface.so with:
# make jsinterface.so

'''
typedef void report_js_info(
	int version, int max_name_length, char* name,
	int buttons, int button_map_size, uint16_t* button_map,
	int axes, int axis_map_size, uint8_t* axis_map,
	int button_name_offset,
	int axis_names_size, char* axis_names,
	int button_names_size, char* button_names
);
'''

report_js_info_prototype = ctypes.CFUNCTYPE(ctypes.c_void_p, 
	#int version, int max_name_length, char* name,
	ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
	#int buttons, int button_map_size, uint16_t* button_map,
	ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint16),
	#int axes, int axis_map_size, uint8_t* axis_map,
	ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint8),
	#int button_name_offset,
	ctypes.c_int,
	#int axis_names_size, char* axis_names,
	ctypes.c_int, ctypes.POINTER(ctypes.c_char_p),
	#int button_names_size, char* button_names
	ctypes.c_int, ctypes.POINTER(ctypes.c_char_p),
)

report_event_prototype = ctypes.CFUNCTYPE(ctypes.c_void_p,
	#int type, int slot, int value
	ctypes.c_int, ctypes.c_int, ctypes.c_int
)


attach_prototype = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, report_js_info_prototype, report_event_prototype)


'''
typedef void report_event(
	int type, int slot, int value
);
'''

import enum, threading, pathlib
js_lib = ctypes.CDLL(pathlib.Path(__file__).parent / 'jsinterface.so')	#Get path from where this python file is

attach = attach_prototype(js_lib.attach)



class input_device(threading.Thread):

	class input_device_state(enum.Enum):
		IDLE = 0
		CONNECTING = 1
		RUNNING = 2
		TERMINATED = 3

	class event_type(enum.IntEnum):
		BUTTON = 1
		AXIS = 2


	def __init__(self, device_node):
		super().__init__()
		self.device_node = bytes(device_node, 'utf-8')
		self.version = None
		self.name = None
		self.axis_name_map = None
		self.button_name_map = None
		self.state = self.input_device_state.IDLE
		self.on_connect = None
		self.on_event = None


	def event_cb(self, ev_type, ev_slot, ev_value):
		if self.on_event:
			self.on_event(self.event_type(ev_type), ev_slot, ev_value)

	def init_cb(self, version, max_name_length, name, buttons, button_map_size, button_map, axes, axis_map_size, axis_map, button_name_offset, axis_names_size, axis_names, button_names_size, button_names):
		self.version = version
		self.name = str(name, 'utf-8')
		self.axis_name_map = {i: str(axis_names[axis_map[i]], 'utf-8') for i in range(axes)}
		self.button_name_map = {i: str(button_names[button_map[i] - button_name_offset], 'utf-8') for i in range(buttons)}
		self.state = self.input_device_state.RUNNING
		if self.on_connect:
			self.on_connect()

	def run(self):
		self.state = self.input_device_state.CONNECTING
		attach(self.device_node, report_js_info_prototype(self.init_cb), report_event_prototype(self.event_cb))
		self.state = self.input_device_state.TERMINATED

	def dump_info(self):
		print(f'Connected to `{self.name}´')
		print(f'Controller has {len(self.axis_name_map)} axises and {len(self.button_name_map)} buttons.')
		for a, n in self.axis_name_map.items():
			print(f'   Axis {a}\t{n}')
		print()
		for b, n in self.button_name_map.items():
			print(f'   Button {b}\t{n}')


def test():

	def event_cb(ev_type, ev_slot, ev_value):
		print('EVENT', locals())

	def info_cb(version, max_name_length, name, buttons, button_map_size, button_map, axes, axis_map_size, axis_map, button_name_offset, axis_names_size, axis_names, button_names_size, button_names, fd):
		print('INFO', locals())
		print()

		axis_name_map = {i: str(axis_names[axis_map[i]], 'utf-8') for i in range(axes)}
		button_name_map = {i: str(button_names[button_map[i] - button_name_offset], 'utf-8') for i in range(buttons)}
		js_name = str(name, 'utf-8')


		print(js_name)
		print(axis_name_map)
		print(button_name_map)

		print()
		print()

	import threading

	test_thread = threading.Thread(target=attach, args=(b'/dev/input/js0', report_js_info_prototype(info_cb), report_event_prototype(event_cb)))
	test_thread.start()


def test2():

	c = input_device('/dev/input/js0')
	c.on_connect = c.dump_info
	c.on_event = print
	c.start()


def test3():
	import socket, json, types, time

	def client_loop(c, addr):
		while True:

			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

			while True:
				try:
					s.connect(addr)
					break
				except Exception as e:
					print('Could not connect', e)
					time.sleep(1)			

			def send_message(**msg):
				try:
					return s.send(bytes(json.dumps(msg), 'utf-8') +b'\n')
				except Exception as e:
					print('EXC', e)

			def send_device_info(device):
				if device.state != device.input_device_state.RUNNING:
					return
				send_message(
					type = 'register_controller',
					name = device.name,
					axises = device.axis_name_map,
					buttons = device.button_name_map,
				)

			def send_event(device, ev_type, ev_slot, ev_value):
				send_message(
					type = 'event',
					data = (int(ev_type), ev_slot, ev_value),
				)

			send_device_info(c)

			#We will register on connecting instead since we should be connected already anyway
			#c.on_connect = types.MethodType(send_device_info, c)
			c.on_event = types.MethodType(send_event, c)

			while True:
				time.sleep(0.3)
				if not send_message(type='heartbeat'):
					print('Lost connection - reconnecting')
					break

	c = input_device('/dev/input/js0')
	c.start()
	client_loop(c, ('target_machine', 8901))
	

test3()
