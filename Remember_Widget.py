import appex
import os
import ui
import shelve
from datetime import date, timedelta
import Remember


def main():
	widget_name = __file__ + str(os.stat(__file__).st_mtime)
	widget_view = appex.get_widget_view()
	if widget_view is None or widget_view.name != widget_name:
		widget_view = Remember.RememberView()
		widget_view.runAsWidget()
		widget_view.name = widget_name
		appex.set_widget_view(widget_view)
		
if __name__ == '__main__':
	main()
