// jsinterface.c was adapted from jstest.c - 
// see jstest.c for copyright and further information

#define _DEFAULT_SOURCE

#include <sys/ioctl.h>
#include <sys/time.h>
#include <sys/types.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include <linux/input.h>
#include <linux/joystick.h>

#include "axbtnmap.h"

char *axis_names[ABS_MAX + 1] = {
"X", "Y", "Z", "Rx", "Ry", "Rz", "Throttle", "Rudder", 
"Wheel", "Gas", "Brake", "?", "?", "?", "?", "?",
"Hat0X", "Hat0Y", "Hat1X", "Hat1Y", "Hat2X", "Hat2Y", "Hat3X", "Hat3Y",
"?", "?", "?", "?", "?", "?", "?", 
};

/* These must match the constants in include/uapi/linux/input.h */
char *button_names[KEY_MAX - BTN_MISC + 1] = {
  /* BTN_0, 0x100, to BTN_9, 0x109 */
  "Btn0", "Btn1", "Btn2", "Btn3", "Btn4", "Btn5", "Btn6", "Btn7", "Btn8", "Btn9",
  /* 0x10a to 0x10f */
  "?", "?", "?", "?", "?", "?",
  /* BTN_LEFT, 0x110, to BTN_TASK, 0x117 */
  "LeftBtn", "RightBtn", "MiddleBtn", "SideBtn", "ExtraBtn", "ForwardBtn", "BackBtn", "TaskBtn",
  /* 0x118 to 0x11f */
  "?", "?", "?", "?", "?", "?", "?", "?",
  /* BTN_TRIGGER, 0x120, to BTN_PINKIE, 0x125 */
  "Trigger", "ThumbBtn", "ThumbBtn2", "TopBtn", "TopBtn2", "PinkieBtn",
  /* BTN_BASE, 0x126, to BASE6, 0x12b */
  "BaseBtn", "BaseBtn2", "BaseBtn3", "BaseBtn4", "BaseBtn5", "BaseBtn6",
  /* 0x12c to 0x12e */
  "?", "?", "?",
  /* BTN_DEAD, 0x12f */
  "BtnDead",
  /* BTN_A, 0x130, to BTN_TR2, 0x139 */
  "BtnA", "BtnB", "BtnC", "BtnX", "BtnY", "BtnZ", "BtnTL", "BtnTR", "BtnTL2", "BtnTR2",
  /* BTN_SELECT, 0x13a, to BTN_THUMBR, 0x13e */
  "BtnSelect", "BtnStart", "BtnMode", "BtnThumbL", "BtnThumbR",
  /* 0x13f */
  "?",
  /* Skip the BTN_DIGI range, 0x140 to 0x14f */
  "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?",
  /* BTN_WHEEL / BTN_GEAR_DOWN, 0x150, to BTN_GEAR_UP, 0x151 */
  "WheelBtn", "Gear up",
};

#define NAME_LENGTH 128

typedef void report_js_info(
	int version, int max_name_length, char* name,
	int buttons, int button_map_size, uint16_t* button_map,
	int axes, int axis_map_size, uint8_t* axis_map,
	int button_name_offset,
	int axis_names_size, char* axis_names[],
	int button_names_size, char* button_names[]
);

typedef void report_event(
	int type, int slot, int value
);

int attach (char* device_node, report_js_info* report_js_info_cb, report_event* report_event_cb) {
	int fd, i;
	unsigned char axes = 2;
	unsigned char buttons = 2;
	int version = 0x000800;
	char name[NAME_LENGTH] = "Unknown";
	uint16_t btnmap[BTNMAP_SIZE];
	uint8_t axmap[AXMAP_SIZE];
	int btnmapok = 1;

	if ((fd = open(device_node, O_RDONLY)) < 0) {
		perror("jstest");
		return 1;
	}

	ioctl(fd, JSIOCGVERSION, &version);
	ioctl(fd, JSIOCGAXES, &axes);
	ioctl(fd, JSIOCGBUTTONS, &buttons);
	ioctl(fd, JSIOCGNAME(NAME_LENGTH), name);

	getaxmap(fd, axmap);
	getbtnmap(fd, btnmap);

	report_js_info_cb(
		version, NAME_LENGTH, name,
		buttons, BTNMAP_SIZE, btnmap,
		axes, AXMAP_SIZE, axmap,
		BTN_MISC,
		ABS_MAX + 1, axis_names,
		KEY_MAX - BTN_MISC + 1, button_names
	);



	/* Determine whether the button map is usable. */
	for (i = 0; btnmapok && i < buttons; i++) {
		if (btnmap[i] < BTN_MISC || btnmap[i] > KEY_MAX) {
			btnmapok = 0;
			return -1;
		}
	}




	struct js_event js;


	while (1) {
		if (read(fd, &js, sizeof(struct js_event)) != sizeof(struct js_event)) {
			perror("\njstest: error reading");
			return 1;
		}

		switch(js.type & ~JS_EVENT_INIT) {
		case JS_EVENT_BUTTON:
			report_event_cb(1, js.number, js.value);
			break;
		case JS_EVENT_AXIS:
			report_event_cb(2, js.number, js.value);
			break;
		}

	}

	return -1;
}
