import ui
import shelve
from datetime import date, datetime, timedelta
from objc_util import *
from console import alert

DISPLAY_WEEKDAY = True
KEYBOARD_HEIGHT = 0  # Will later be set to correct value by method call when keyboard is displayed
LIST_INSET = 50
NAME_INPUT_HEIGHT = 35
DATE_PICKER_HEIGHT = NAME_INPUT_HEIGHT * 4
REPEAT_BAR_HEIGHT = NAME_INPUT_HEIGHT
CHOOSE_COLOUR_BAR_HEIGHT = REPEAT_BAR_HEIGHT
DATE_BUTTON_WIDTH = 30
DATE_BUTTON_SPACE = 10
REPEAT_BUTTON_SPACE = 5
TOP_BAR_HEIGHT = 45
STATUS_BAR_HEIGHT = 52  # Space allowed for the status bar
EDIT_BUTTON_WIDTH = 47
EDIT_BUTTON_HEIGHT = 23
EDIT_BUTTON_SPACE = 2

def get_text_colour(colour):
	luminance = 0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2]
	return 'black' if luminance > 0.2 else 'lightgrey'


class Reminder (object):
	def __init__(self, name, colour, repeat=[], start_date=None, end_date=None):
		self.name = name
		self.colour = colour  # tuple of rgb values in range 0-1
		self.repeat = repeat  # list of weekdays this event repeats
		self.start_date = start_date  # for repeating events
		self.end_date = end_date  # for repeating events
	
	def equal_to(self, other):
		return self.name == other.name and self.colour == other.colour and self.repeat == other.repeat and self.start_date == other.start_date and self.end_date == other.end_date


class ReminderHandler (object):
	def __init__(self, parent):
		self.load()
		self.parent = parent
		self.editing_date = None
		self.editing_reminder = None
		
	def tableview_number_of_sections(self, tableview):
		# Return the number of sections (defaults to 1)
		return len(self.get_enabled_dates())
		
	def tableview_number_of_rows(self, tableview, section):
		# Return the number of rows in the section
		return len(self.get_enabled_events(self.get_enabled_dates()[section]))
		
	def get_reminder(self, section, row):
		return self.get_enabled_events(self.get_enabled_dates()[section])[row]
		
	def tableview_cell_for_row(self, tableview, section, row):
		# Create and return a cell for the given section/row
		cell = ui.TableViewCell()
		cell.bg_color = self.all_colours[self.get_reminder(section, row).colour]
		cell.text_label.text_color = get_text_colour(cell.bg_color)
		
		cell.text_label.text = self.get_reminder(section, row).name
		return cell
		
	def tableview_title_for_header(self, tableview, section):
		# Return a title for the given section.
		# If this is not implemented, no section headers will be shown.

		d = self.get_enabled_dates()[section]
		if d == 'Remember':
			return d
		
		day_str = str(d.day)
		weekday = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][d.weekday()]
		month = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
				 'August', 'September', 'October', 'November', 'December'][d.month - 1]
		
		close = ''
		if abs((d - self.parent.today).days) < 2:
			days = d.weekday() - self.parent.today.weekday() % 7
			if days < 0:
				days += 7
			if days == 0:
				close = 'Today - '
			elif days == 1:
				close = 'Tomorrow - '
			else: 
				close = 'Yesterday - '  # -1 is the only other option
			
		section_name = close + ((weekday + ', ') if DISPLAY_WEEKDAY else '')
		section_name += month + ' ' + day_str
		if day_str.endswith('1') and day_str != '11':
			section_name += 'st'
		elif day_str.endswith('2') and day_str != '12':
			section_name += "nd"
		elif day_str.endswith('3') and day_str != '13':
			section_name += "rd"
		else:
			section_name += "th"

		if d.year != self.parent.today.year:
			section_name += ', ' + str(d.year)
		
		return section_name
		
	def tableview_can_delete(self, tableview, section, row):
		# Return True if the user should be able to delete the given row.
		return True
		
	def tableview_can_move(self, tableview, section, row):
		# Return True if a reordering control should be shown for the given row (in editing mode).
		return True
		
	def tableview_delete(self, tableview, section, row):
		# Called when the user confirms deletion of the given row.
		date = self.get_enabled_dates()[section]
		reminder = self.get_reminder(section, row)
		
		if reminder.repeat:
			try:
				x = alert('Delete Repeated Event', 'Would you like to delete all occurrences of the event?',
						  'Delete One', 'Delete All')
			except KeyboardInterrupt:
				x = 0
			if x == 0:
				return
			elif x == 1:
				self.remove_event(reminder, date)
			elif x == 2:
				self.remove_repeat_events_in_range(reminder, reminder.start_date, reminder.end_date)
		else:
			self.remove_event(reminder, date)
		
		self.update(tableview)
		
	def tableview_move_row(self, tableview, from_section, from_row, to_section, to_row):
		# Called when the user moves a row with the reordering control (in editing mode).
		if from_section == to_section and from_row == to_row:
			return
		
		reminder = self.get_reminder(from_section, from_row)
		date = self.get_enabled_dates()[to_section]
		self.tableview_delete(tableview, from_section, from_row)
		
		if len(self.events[date]) > to_row:
			self.events[date].insert(to_row, reminder)
		else:
			self.events[date].append(reminder)
		self.update(tableview)
		
	# Delegate Functions
	
	def tableview_did_select(self, tableview, section, row):
		reminder = self.get_reminder(section, row)
		date = self.get_enabled_dates()[section]
		self.editing_date = date
		self.editing_reminder = reminder
		if date == 'Remember':
			self.parent.date_picker.enabled = False
		else:
			self.parent.date_picker.date = datetime.combine(date, datetime.min.time())
			self.parent.repeat_end_date_picker.date = datetime.combine(reminder.end_date, datetime.min.time())
			self.parent.date_picker.enabled = True
			
		for b in self.parent.choose_colour_buttons:
			b.title = ''
		for i in range(7):
			if i in reminder.repeat:
				self.parent.repeat_buttons[i].border_width = 2
			else:
				self.parent.repeat_buttons[i].border_width = 0
		
		self.parent.choose_colour_buttons[reminder.colour].title = '✓'
		self.parent.show_input_view()
		self.parent.name_input.text = reminder.name
		
	def tableview_did_deselect(self, tableview, section, row):
		# Called when a row was de-selected (in multiple selection mode).
		pass
		
	def tableview_title_for_delete_button(self, tableview, section, row):
		return 'Delete'
		
	def add_event(self, name, colour, repeat, date, end_date):
		if not repeat:
			end_date = date
		
		reminder = Reminder(name, colour, repeat, date, end_date)
		
		deleted_dates = set()
		extra_dates = set()
		if self.editing_reminder is not None:
			reminder.start_date = self.editing_reminder.start_date if self.editing_reminder.start_date != 'Remember' else date
			
			if date == self.editing_date and self.editing_reminder.repeat == [] and repeat == []:
				self.events[date][self.events[date].index(self.editing_reminder)] = reminder
				self.editing_date = None
				self.editing_reminder = None
				return
			
			if repeat:
				if date.weekday() not in repeat:
					extra_dates.add(date)
					
				if date != self.editing_date:
					deleted_dates.add(self.editing_date)
					do_not_delete = date
				else:
					do_not_delete = None
						
				if self.editing_date != 'Remember':
					date = self.editing_date if self.editing_reminder.repeat == [] else reminder.start_date
				
				if self.editing_reminder.repeat:
					while date <= self.editing_reminder.end_date:
						if date.weekday() in repeat:
							if date in self.events.keys():
								if not any(e.equal_to(self.editing_reminder) for e in self.events[date]):
									deleted_dates.add(date)
							else:
								deleted_dates.add(date)
								
						elif date in self.events.keys() and any(e.equal_to(self.editing_reminder) for e in self.events[date]):
							extra_dates.add(date)
							
						date += timedelta(days=1)
					
				if do_not_delete in deleted_dates:
					deleted_dates.remove(do_not_delete)
				extra_dates = {d for d in extra_dates if d not in deleted_dates}
				
			self.remove_event(self.editing_reminder, self.editing_date, True)
				
			self.editing_date = None
			self.editing_reminder = None
			
		if repeat:
			date = reminder.start_date
			while date <= end_date:
				if date not in deleted_dates and date.weekday() in repeat:
					if date in self.events.keys():
						self.events[date].append(reminder)
					else:
						self.events[date] = [reminder]
				date += timedelta(days=1)
				
			for date in extra_dates:
				if date in self.events.keys():
					self.events[date].append(reminder)
				else:
					self.events[date] = [reminder]
				
		else:
			if date in self.events.keys():
				self.events[date].append(reminder)
			else:
				self.events[date] = [reminder]
			
		self.dates = sorted([i for i in self.events.keys() if i != 'Remember'])
		if 'Remember' in self.events.keys():
			self.dates.insert(0, 'Remember')
			
		self.editing_date = None
		self.editing_reminder = None
			
				
	def remove_event(self, reminder, date, remove_repeats=False):
		self.events[date].remove(reminder)
		if not self.events[date]:
			self.events.pop(date)
			self.dates.remove(date)
			
		if remove_repeats and reminder.repeat != []:
			self.remove_repeat_events_in_range(reminder, reminder.start_date, reminder.end_date)
			
	def remove_repeat_events_in_range(self, event, start, end):
		date = start
		while date <= end:
			if date in self.events.keys():
				self.events[date] = [e for e in self.events[date] if not e.equal_to(event)]
				if not self.events[date]:
					self.events.pop(date)
					self.dates.remove(date)
			date += timedelta(days=1)
		
	def update(self, tableview=None):
		self.save()
		if tableview:
			tableview.reload_data()

	def load(self):
		with shelve.open('Remember') as file:
			if not 'events' in file.keys():
				file['events'] = {}
				
			self.events = file['events']
			
			self.dates = sorted([i for i in self.events.keys() if i != 'Remember'])
			if 'Remember' in self.events.keys():
				self.dates.insert(0, 'Remember')
					
			self.save()
						
		self.all_colours = [(1, 1, 1), (1, 0, 0), (1, 0.5, 0),
		(1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), (0, 0, 0)]
		self.enabled = [True] * len(self.all_colours)
						
	def save(self):
		with shelve.open('Remember', flag='n') as file:
			file['events'] = self.events
			
	def get_enabled_dates(self):
		return [d for d in self.dates if any(self.enabled[e.colour] for e in self.events[d])]
		
	def get_enabled_events(self, date):
		return [e for e in self.events[date] if self.enabled[e.colour]]
			
class NameInputDelegate (object):
	def __init__(self, parent):
		self.parent = parent
		
	def textfield_should_begin_editing(self, textfield):
		return True
		
	def textfield_did_begin_editing(self, textfield):
		pass
		
	def textfield_did_end_editing(self, textfield):
		self.parent.reminder_entered()
		
	def textfield_should_return(self, textfield):
		textfield.end_editing()
		return True
		
	def textfield_should_change(self, textfield, range, replacement):
		return True
		
	def textfield_did_change(self, textfield):
		pass
		
class RememberView (ui.View):
	def __init__(self, *args, **kwargs):
		super().__init__(self, *args, **kwargs)
		self.shows_result = False
		self.bounds = (0, 0, 400, 400)
		self.background_color = 'white'
		self.today = date.today()
		
		self.isWidget = True
		
		self.reminders_view = ui.TableView()
		self.reminders_view.data_source = ReminderHandler(self)
		self.reminders_view.delegate = self.reminders_view.data_source
		self.reminders_view.allows_selection = True
		self.add_subview(self.reminders_view)
		
		weekday = self.today.weekday()
		weekdays = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
		
		self.button_view = ui.ScrollView()
		self.button_view.background_color = 'lightgray'
		self.add_subview(self.button_view)
		
		self.colour_view = ui.ScrollView()
		self.colour_view.background_color = 'white'
		
		self.choose_colour_view = ui.ScrollView()
		self.choose_colour_view.background_color = 'white'
		
		self.top_bar = ui.View()
		self.top_bar.background_color = 'white'
		self.add_subview(self.top_bar)
		
		self.input_view = ui.View()
		self.input_view.background_color = 'white'
		self.add_subview(self.input_view) 
		
		button_style = {'background_color': (1, 0, 0, 1), 'tint_color': 'white', 'font': ('HelveticaNeue-Light', 18), 'corner_radius': 3, 'border_width': 1.5}
		
		weekdays_wrapped = weekdays[weekday:] + weekdays[:weekday]
		button_list = weekdays_wrapped + [str((self.today + timedelta(days=n)).day) for n in range(7, 30 if self.today.month in [4, 6, 9, 11] else 31)]
		
		remember_button = ui.Button(image=ui.Image.named('typw:Edit'), action=self.remember_button_pressed, name=str('Remember'), **button_style)
		self.date_buttons = [remember_button]
		self.button_view.add_subview(remember_button)
	
		for i, d in enumerate(button_list):
			b = ui.Button(title=d, action=self.date_button_pressed, name=str(i), **button_style)
			self.date_buttons.append(b)
			self.button_view.add_subview(b)
			
		self.repeat_buttons = []
		for i, d in enumerate(weekdays):
			b = ui.Button(title=d, action=self.repeat_button_pressed, name=str(i), **button_style)
			self.repeat_buttons.append(b)
			self.input_view.add_subview(b)
			
		self.colour_buttons = []
		for i, c in enumerate(self.reminders_view.data_source.all_colours):
			b = ui.Button(title='✓', action=self.colour_button_pressed, name=str(i), **button_style)
			b.background_color = c
			b.tint_color = get_text_colour(b.background_color)
			self.colour_buttons.append(b)
			self.colour_view.add_subview(b)
			
		self.choose_colour_buttons = []
		for i, c in enumerate(self.reminders_view.data_source.all_colours):
			b = ui.Button(title='✓' if i == 0 else '', action=self.choose_colour_button_pressed, name=str(i), **button_style)
			b.background_color = c
			b.tint_color = get_text_colour(b.background_color)
			self.choose_colour_buttons.append(b)
			self.choose_colour_view.add_subview(b)
			
		self.edit_button = ui.Button(title='Edit', action=self.edit_button_pressed, **button_style)
		self.top_bar.add_subview(self.edit_button)
		self.top_bar.add_subview(self.colour_view)
		
		self.name_input = ui.TextField()
		self.name_input.delegate = NameInputDelegate(self)
		self.name_input.corner_radius = 4
		self.name_input.clear_button_mode = 'while_editing'
		self.name_input.autocapitalization_type = ui.AUTOCAPITALIZE_WORDS
		
		self.date_picker = ui.DatePicker()
		self.input_view.add_subview(self.date_picker)
		self.date_picker.hidden = True
		self.date_picker.mode = ui.DATE_PICKER_MODE_DATE
		
		self.repeat_end_date_picker = ui.DatePicker()
		self.input_view.add_subview(self.repeat_end_date_picker)
		self.repeat_end_date_picker.hidden = True
		self.repeat_end_date_picker.mode = ui.DATE_PICKER_MODE_DATE
		
		self.repeat_end_date_label = ui.Label(text='End Date:', font=('HelveticaNeue-Light', 18))
		self.input_view.add_subview(self.repeat_end_date_label)
		
		self.input_view.add_subview(self.choose_colour_view)
		self.input_view.add_subview(self.name_input)
		self.input_view.background_color = (1, 1, 1)
		self.input_view.hidden = True
		
		self.daysAway = 0
		
	def layout(self):
		show_repeat_end_date = any(b.border_width > 0 for b in self.repeat_buttons)
		
		self.reminders_view.frame = self.bounds.inset(TOP_BAR_HEIGHT, 0, 0, LIST_INSET)
		
		for i, button in enumerate(self.date_buttons):
			button.frame = ui.Rect((self.button_view.bounds.width - DATE_BUTTON_WIDTH) / 2, (DATE_BUTTON_SPACE / 2) + i * (DATE_BUTTON_SPACE + DATE_BUTTON_WIDTH), DATE_BUTTON_WIDTH, DATE_BUTTON_WIDTH)
			button.corner_radius = button.frame.width / 2
			
		
		self.button_view.frame = self.bounds.inset(TOP_BAR_HEIGHT, self.bounds.width - LIST_INSET, 0, 0)
		
		self.button_view.content_size = (self.button_view.frame.width, button.frame.y + button.frame.height + (DATE_BUTTON_SPACE / 2))
		
		self.top_bar.frame = self.bounds.inset(0, 0, self.bounds.height - TOP_BAR_HEIGHT, 0)
		
		input_view_height = NAME_INPUT_HEIGHT + REPEAT_BAR_HEIGHT + DATE_PICKER_HEIGHT + CHOOSE_COLOUR_BAR_HEIGHT
		
		if show_repeat_end_date:
			input_view_height += DATE_PICKER_HEIGHT + NAME_INPUT_HEIGHT
			self.repeat_end_date_picker.hidden = False
			self.repeat_end_date_label.hidden = False
		else:
			self.repeat_end_date_picker.hidden = True
			self.repeat_end_date_label.hidden = False
			
		self.input_view.frame = ui.Rect(0, min(self.height, KEYBOARD_HEIGHT - STATUS_BAR_HEIGHT) - input_view_height, self.width - LIST_INSET, input_view_height)
	
		self.name_input.frame = ui.Rect(0, input_view_height - NAME_INPUT_HEIGHT, self.input_view.frame.width, NAME_INPUT_HEIGHT)
		
		self.date_picker.frame = ui.Rect(0, 0, self.input_view.frame.width, DATE_PICKER_HEIGHT)
		
		self.repeat_end_date_picker.frame = ui.Rect(0, DATE_PICKER_HEIGHT + REPEAT_BAR_HEIGHT + NAME_INPUT_HEIGHT, self.input_view.frame.width, DATE_PICKER_HEIGHT)
		
		self.choose_colour_view.frame = ui.Rect(0, input_view_height - NAME_INPUT_HEIGHT - CHOOSE_COLOUR_BAR_HEIGHT, self.input_view.frame.width, CHOOSE_COLOUR_BAR_HEIGHT)
		
		self.repeat_end_date_label.frame = ui.Rect(REPEAT_BUTTON_SPACE, DATE_PICKER_HEIGHT + REPEAT_BAR_HEIGHT, self.input_view.frame.width, NAME_INPUT_HEIGHT)
		
		self.colour_view.frame = self.top_bar.bounds.inset(0, 0, 0, EDIT_BUTTON_WIDTH + EDIT_BUTTON_SPACE * 2)
		
		self.edit_button.frame = ui.Rect(self.top_bar.bounds.width - (EDIT_BUTTON_SPACE + EDIT_BUTTON_WIDTH), (self.top_bar.bounds.height - EDIT_BUTTON_HEIGHT) / 2, EDIT_BUTTON_WIDTH, EDIT_BUTTON_HEIGHT)
		
		for i, button in enumerate(self.colour_buttons):
			button.frame = ui.Rect((DATE_BUTTON_SPACE / 2) + i * (DATE_BUTTON_SPACE + DATE_BUTTON_WIDTH), (self.colour_view.bounds.height - DATE_BUTTON_WIDTH) / 2, DATE_BUTTON_WIDTH, DATE_BUTTON_WIDTH)
			button.corner_radius = button.frame.width / 2
			
		for i, button in enumerate(self.choose_colour_buttons):
			button.frame = ui.Rect((REPEAT_BUTTON_SPACE / 2) + i * (REPEAT_BUTTON_SPACE + DATE_BUTTON_WIDTH), (self.choose_colour_view.bounds.height - DATE_BUTTON_WIDTH) / 2, DATE_BUTTON_WIDTH, DATE_BUTTON_WIDTH)
			button.corner_radius = button.frame.width / 2
			
		self.colour_view.content_size = (self.button_view.frame.width, button.frame.y + button.frame.height + (DATE_BUTTON_SPACE / 2))
		self.choose_colour_view.content_size = (self.button_view.frame.width, button.frame.y + button.frame.height + (DATE_BUTTON_SPACE / 2))
		
		for i, button in enumerate(self.repeat_buttons):
			button.frame = ui.Rect((REPEAT_BUTTON_SPACE / 2) + i * (REPEAT_BUTTON_SPACE + DATE_BUTTON_WIDTH), DATE_PICKER_HEIGHT + (REPEAT_BAR_HEIGHT - DATE_BUTTON_WIDTH) / 2, DATE_BUTTON_WIDTH, DATE_BUTTON_WIDTH)
			button.corner_radius = button.frame.width / 2
			
	def date_button_pressed(self, sender):
		self.date_picker.date = datetime.combine(self.today + timedelta(days=int(sender.name)), datetime.min.time())
		self.date_picker.enabled = True
		
		if self.input_view.hidden:
			for b in self.choose_colour_buttons:
				b.title = ''
			self.choose_colour_buttons[0].title = '✓'
			for b in self.repeat_buttons:
				b.border_width = 0
			self.repeat_end_date_picker.date = self.date_picker.date
			self.show_input_view()
			self.layout()
			
	def remember_button_pressed(self, sender):
		self.date_picker.enabled = False
		
		if self.input_view.hidden:
			for b in self.choose_colour_buttons:
				b.title = ''
			self.choose_colour_buttons[0].title = '✓'
			self.show_input_view()
		
		for b in self.repeat_buttons:
			b.border_width = 0
		self.layout()
		
	def repeat_button_pressed(self, sender):
		if self.date_picker.enabled:
			if sender.border_width == 0:
				sender.border_width = 2
			else:
				sender.border_width = 0
			self.layout()
		
		
	def colour_button_pressed(self, sender):
		checked = sender.title == ''
		
		self.reminders_view.data_source.enabled[int(sender.name)] = checked
		sender.title = '✓' if checked else ''
		self.reminders_view.data_source.update(self.reminders_view)
		
	def choose_colour_button_pressed(self, sender):
		if sender.title == '':
			for b in self.choose_colour_buttons:
				b.title = ''
			sender.title = '✓'
		
	def show_input_view(self):
		if self.input_view.hidden:
			self.input_view.hidden = False
			self.date_picker.hidden = False
			self.name_input.begin_editing()
			
	def edit_button_pressed(self, sender):
		if sender.title == 'Edit':
			self.reminders_view.editing = True
			sender.title = 'Done'
		else:
			self.reminders_view.editing = False
			sender.title = 'Edit'
			
	def reminder_entered(self):
		self.input_view.hidden = True
		event_name = self.name_input.text
		if event_name.isspace() or event_name == '': return
		self.name_input.text = ''
		
		repeat = []
		for i, b in enumerate(self.repeat_buttons):
			if b.border_width > 0:
				repeat.append(i)
				
		if self.date_picker.enabled:
			event_date = self.date_picker.date.date()
			end_date = self.repeat_end_date_picker.date.date()
		else:
			end_date = None
			event_date = 'Remember'
			
		for i, b in enumerate(self.choose_colour_buttons):
			if b.title != '':
				colour = i
				break

		self.reminders_view.data_source.add_event(event_name, colour, repeat, event_date, end_date)
		self.reminders_view.data_source.update(self.reminders_view)
		self.button_view.content_offset = (0, 0)
		
	def run_as_widget(self):
		self.isWidget = True
		
	def run_as_app(self):
		self.isWidget = False
		
		
def keyboardWillShow_(_self, _cmd, n):
	global KEYBOARD_HEIGHT
	if KEYBOARD_HEIGHT == 0:
		notification = ObjCInstance(n)
		rect = notification.userInfo()['UIKeyboardFrameEndUserInfoKey']
		KEYBOARD_HEIGHT = int(str(rect).split()[2][:-2])
		global v
		v.layout()
	
def main():
	global v
	v = RememberView()
	
	center = ObjCClass('NSNotificationCenter').defaultCenter()

	KeyboardObserver = create_objc_class('KeyboardObserver', methods=[keyboardWillShow_])
	observer = KeyboardObserver.alloc().init()
	
	center.addObserver_selector_name_object_(observer, 'keyboardWillShow:', 'UIKeyboardDidShowNotification', None)
	
	v.run_as_app()
	v.present('sheet', hide_title_bar=True, hide_close_button=True)
	
if __name__ == '__main__':
	main()
	
