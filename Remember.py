import ui
import shelve
from datetime import date, timedelta
import Remember

def stringToDate(string):
	'''Changes a date from the string representation used for storing (ex. '180211') and changes it to a datetime.date object.'''
	divided = [int(string[i:i+2]) for i in range(0, len(string), 2)]
	divided[0] += 2000
	return date(*divided)
	
def dateToString(date):
	return ('%02d' % (date.year - 2000)) + ('%02d' % date.month) + ('%02d' % date.day)

class ReminderStorer (object):
	def __init__(self, parent):
		self.load()
		self.parent = parent
		self.editing = None
		
	def tableview_number_of_sections(self, tableview):
		# Return the number of sections (defaults to 1)
		return len(self.dates)
		
	def tableview_number_of_rows(self, tableview, section):
		# Return the number of rows in the section
		return len(self.events[self.dates[section]])
		
	def tableview_cell_for_row(self, tableview, section, row):
		# Create and return a cell for the given section/row
		cell = ui.TableViewCell()
		cell.bg_color = (0, 1, 0, 0.6)
		cell.text_label.text = self.events[self.dates[section]][row]
		return cell
		
	def tableview_title_for_header(self, tableview, section):
		# Return a title for the given section.
		# If this is not implemented, no section headers will be shown.
		
		DISPLAY_WEEKDAY = True
		d = stringToDate(self.dates[section])
		daystr = str(d.day)
		weekday = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][d.weekday()]
		month = [0, 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][d.month]
		
		close = ''
		if abs((d - date.today()).days) < 2:
			days = d.weekday() - date.today().weekday() % 7
			if days < 0: days += 7
			if days == 0: close = 'Today - '
			elif days == 1: close = 'Tomorrow - '
			else: close = 'Yesterday - ' # -1 is the only other option
		
		return close + ((weekday + ', ') if DISPLAY_WEEKDAY else '') + month + ' ' + daystr + ('st' if (daystr.endswith('1') and daystr != '11') else 'nd' if (daystr.endswith('2') and daystr != '12') else 'rd' if (daystr.endswith('3') and daystr != '13') else 'th') + ((', ' + str(d.year)) if d.year != date.today().year else '')
		
	def tableview_can_delete(self, tableview, section, row):
		# Return True if the user should be able to delete the given row.
		return True
		
	def tableview_can_move(self, tableview, section, row):
		# Return True if a reordering control should be shown for the given row (in editing mode).
		return True
		
	def tableview_delete(self, tableview, section, row):
		# Called when the user confirms deletion of the given row.
		
		self.events[self.dates[section]].remove(self.events[self.dates[section]][row])
		if self.events[self.dates[section]] == []:
			self.events.pop(self.dates[section])
			self.dates.remove(self.dates[section])
		self.update(tableview)
		
	def tableview_move_row(self, tableview, from_section, from_row, to_section, to_row):
		# Called when the user moves a row with the reordering control (in editing mode).
		name = self.events[self.dates[from_section]][from_row]
		date = self.dates[to_section]
		self.tableview_delete(tableview, from_section, from_row)
		self.addEvent(name, date)
		self.update(tableview)
		
	# Delegate Functions
		
	def tableview_did_select(self, tableview, section, row):
		name = self.events[self.dates[section]][row]
		date = self.dates[section]
		self.editing = (date, name)
		print(self.editing)
		self.parent.showNameInput()

	def tableview_did_deselect(self, tableview, section, row):
		# Called when a row was de-selected (in multiple selection mode).
		pass

	def tableview_title_for_delete_button(self, tableview, section, row):
		return 'Delete'
		
	def addEvent(self, name, date):
		if not isinstance(date, str): date = dateToString(date)
		
		if self.editing is not None:
			self.events[self.editing[0]][self.events[self.editing[0]].index(self.editing[1])] = name
			self.editing = None
			return
			
		else:
			if date in self.events.keys():
				self.events[date].append(name)
			else:
				self.events[date] = [name]
			self.dates = sorted([i for i in self.events.keys()])
		
		
		return self.dates.index(date), self.events[date].index(name)
		
	def update(self, tableview=None):
		self.save()
		if tableview: tableview.reload_data()
		
	def load(self):
		with shelve.open('Remember') as file:
			if not 'events' in file.keys():
				file['events'] = {}
				file['dates'] = []
				
			self.events = file['events']
			self.dates = file['dates']
			
			# Testing: adding events that repeat weekly
			ADD_REPEATED_EVENTS = False
			if not ADD_REPEATED_EVENTS: return
			
			self.repeatedEvents = {}
			REPEAT = 20
			for eventWeekday in self.repeatedEvents.keys():
				for event in self.repeatedEvents[eventWeekday]:
					eventDay = date.today() + timedelta(days=(eventWeekday - date.today().weekday()) % 7)
					for i in range(REPEAT):
						self.addEvent(event, eventDay)
						eventDay += timedelta(weeks=1)
						
			
	def save(self):
		with shelve.open('Remember') as file:
			file['events'] = self.events
			file['dates'] = self.dates
		
class NameInputDelegate (object):
	def __init__(self, parent):
		self.parent = parent
	
	def textfield_should_begin_editing(self, textfield):
		return True
	
	def textfield_did_begin_editing(self, textfield):
		pass
	
	def textfield_did_end_editing(self, textfield):
		self.parent.nameInputted()
		
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
		
		self.isWidget = True
		
		self.remindersView = ui.TableView()
		self.remindersView.data_source = ReminderStorer(self)
		self.remindersView.delegate = self.remindersView.data_source
		self.remindersView.allows_selection = True
		self.add_subview(self.remindersView)
		
		weekday = date.today().weekday()
		weekdays = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
		
		self.buttonView = ui.ScrollView()
		self.buttonView.background_color = 'lightgray'
		self.add_subview(self.buttonView)
		
		self.topBar = ui.View()
		self.topBar.background_color = 'white'
		self.add_subview(self.topBar)
		
		
		button_style = {'background_color': (1, 0, 0, 1), 'tint_color': 'white', 'font': ('HelveticaNeue-Light', 18), 'corner_radius': 3}
		self.dateButtons = []
		weekdaysWrapped = weekdays[weekday:] + weekdays[:weekday]
		buttonList = ['...'] + weekdaysWrapped + [str((date.today() + timedelta(days=n)).day) for n in range(7, 100 if date.today().month in [4, 6, 9, 11] else 31)]
		
		for i, d in enumerate(buttonList):
			#i = (i + weekday) % 7
			self.dateButtons.append(ui.Button(title=d, action=self.dateButtonPressed, name=str(i), **button_style))
			
		for button in self.dateButtons: self.buttonView.add_subview(button)
		
		self.editButton = ui.Button(title='Edit', action=self.editButtonPressed, **button_style)
		self.topBar.add_subview(self.editButton)
		
		self.nameInput = ui.TextField()
		self.nameInput.delegate = NameInputDelegate(self)
		self.nameInput.corner_radius = 4
		self.nameInput.hidden = True
		self.nameInput.clear_button_mode = 'while_editing'
		self.nameInput.autocapitalization_type = ui.AUTOCAPITALIZE_WORDS
		self.add_subview(self.nameInput)
		
		self.daysAway = 0
	
	def layout(self):
		#print('Changing size to: ', self.width, self.height)
		LIST_INSET = 50
		NAME_INPUT_HEIGHT = 35
		DATE_BUTTON_WIDTH = 30
		DATE_BUTTON_SPACE = 10
		KEYBOARD_HEIGHT = 286
		TOP_BAR_HEIGHT = 30
		EDIT_BUTTON_WIDTH = 47
		EDIT_BUTTON_HEIGHT = 23
		EDIT_BUTTON_SPACE = 2
		SCREEN_HEIGHT = ui.get_screen_size().h - (80 if self.isWidget else 36)
		
		self.remindersView.frame = self.bounds.inset(TOP_BAR_HEIGHT, 0, 0, LIST_INSET)
		
		self.buttonView.frame = self.bounds.inset(TOP_BAR_HEIGHT, self.bounds.width - LIST_INSET, 0, 0)
		
		self.topBar.frame = self.bounds.inset(0, 0, self.bounds.height - TOP_BAR_HEIGHT, 0)
		
		for i, button in enumerate(self.dateButtons):
			button.frame = ui.Rect((self.buttonView.bounds.width / 2) - (DATE_BUTTON_WIDTH / 2), (DATE_BUTTON_SPACE / 2) + i * (DATE_BUTTON_SPACE + DATE_BUTTON_WIDTH), DATE_BUTTON_WIDTH, DATE_BUTTON_WIDTH)
			button.corner_radius = button.frame.width / 2
			
		self.editButton.frame = ui.Rect(self.topBar.bounds.width - (EDIT_BUTTON_SPACE + EDIT_BUTTON_WIDTH), (self.topBar.bounds.height - EDIT_BUTTON_HEIGHT) / 2, EDIT_BUTTON_WIDTH, EDIT_BUTTON_HEIGHT)
		
		self.buttonView.content_size = (self.buttonView.frame.width, button.frame.y + button.frame.height + (DATE_BUTTON_SPACE / 2))
			
		self.nameInput.frame = ui.Rect(0, min(self.height - NAME_INPUT_HEIGHT, SCREEN_HEIGHT - KEYBOARD_HEIGHT - NAME_INPUT_HEIGHT), self.width - LIST_INSET, NAME_INPUT_HEIGHT)
	
	def dateButtonPressed(self, sender):
		self.daysAway = int(sender.name) - 1
		self.showNameInput()
		
	def showNameInput(self):
		if self.nameInput.hidden:
			self.nameInput.hidden = False
			self.nameInput.begin_editing()
			
		
	def editButtonPressed(self, sender):
		if sender.title == 'Edit':
			self.remindersView.editing = True
			sender.title = 'Done'
		else:
			self.remindersView.editing = False
			sender.title = 'Edit'
		
	def nameInputted(self):
		self.nameInput.hidden = True
		eventName = self.nameInput.text
		if eventName.isspace() or eventName == '': return
		self.nameInput.text = ''
		eventDate = date.today() + timedelta(days=self.daysAway)
		self.remindersView.data_source.addEvent(eventName, eventDate)
		self.remindersView.data_source.update(self.remindersView)
		self.buttonView.content_offset = (0, 0)
		
	def runAsWidget(self):
		self.isWidget = True
		
	def runAsApp(self):
		self.isWidget = False
		
def main():
	v = RememberView()
	v.runAsApp()
	v.present('sheet')

if __name__ == '__main__':
	main()
