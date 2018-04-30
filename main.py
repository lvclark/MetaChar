# class definitions for interactive editable character sheet

from copy import copy
from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.pagelayout import PageLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import os
from inspect import getargspec

version_str = "0.0"

# how much of the vertical space of a horizontal bar should a button take up
mybtn_size_hint_y = 1
# minimum height of a bar or button, in pixels
myminheight = 40
# how wide should the left column be in edit popups
edpop_left_col_size = 0.3
# token to indicate whether there is a edit window open, in which case paging with arrow keys is suppressed
edit_window_open = 0

# a list to hold all stats for the whole character sheet
masterstatlist = []
# find all stats available to include in calculations
def find_stats_for_calc():
    return [s for s in masterstatlist if s.calcavail]
# update the text displayed for all stat values
def update_all_stat_text():
    [s.update_button_text() for s in masterstatlist if isinstance(s, StatBarSimple) or isinstance(s, StatBarSum) \
     or isinstance(s, StatBarFraction)]
     
# sanitize text input for saving and loading
def sanitize_text(string):
    string = string.replace("<", "")
    string = string.replace(">", "")
    return string
     
# recursively read XML-style tags and values from a string. (for loading files)
def read_xml(string):
    # find starting tag <tag>
    first_tag_start = string.find("<")
    first_tag_end = string.find(">")
    tag = string[first_tag_start+1:first_tag_end] # without the brackets
    # trim off starting tag from string
    string = string[first_tag_end+1:]
    # find the ending tag </tag>
    end_marker = "</" + tag + ">"
    end_marker_start = string.find(end_marker)
    # get the string inside the tag
    innerstring = string[:end_marker_start]
    # trim the string to what is after the ending tag
    string = string[(end_marker_start + len(end_marker)):]
    
    # tag and value if this is innermost pair
    if "<" not in innerstring:
        thistv = [tag, innerstring]
    # further search for tags within the value
    else:
        thistv = [tag, read_xml(innerstring)]
    # list of tag value pairs for the string
    tvlist = [thistv]
    # get tag-value pairs for the remainder of the string
    if "<" in string:
        tvlist.extend(read_xml(string))    
    return(tvlist)
# function for converting True and False in file to boolean
def conv_bool(string):
    return string == "True"
# function for converting strings to lists of stats
def conv_statlist(string):
    return [masterstatlist[int(i)] for i in string.split(',') if i != '']
# function for converting index of a single stat
def conv_stat(string):
    if string == 'None':
        return None
    else:
        return masterstatlist[int(string)]
# dictionary to convert strings loaded from file to right class
conv_fns = {'statname': str, 'statdesc': str, 'calcavail': conv_bool,
            'statval': int, 'showplus': conv_bool, 
            'statlist_existing': conv_statlist, 'childstats.statlist': conv_statlist,
            'statbtn.size_hint_x': float, 'stat_to_div': conv_stat, 'divisor': int,
            'rounddown': conv_bool, 'stattext': str, 'defaultval': int,
            'currentval': int, 'statname2': str, 'statdesc2': str, 'statname3': str,
            'statdesc3': str, 'red_bg': float, 'green_bg': float, 'blue_bg': float,
            'statlist': conv_statlist}
# set of arguments that are used for StatBar initialization that might be read from file
initargs = {'statname', 'statdesc', 'calcavail', 'statval', 'showplus', 'statlist_existing',
            'stat_to_div', 'divisor', 'rounddown', 'stattext', 'defaultval', 
            'statname2', 'statdesc2', 'statname3', 'statdesc3'}

# Popup for description of statistics
class DescPopup(Popup):
    desc_lbl = ObjectProperty(None)
    def __init__(self, statdesc, **kwargs):
        Popup.__init__(self, **kwargs)
        self.statdesc = statdesc
        # label made in the .kv file
        self.desc_lbl.text = self.statdesc
    def on_touch_up(self, touch):
        self.dismiss()

# A button with the name of a stat, which you can press to get a description
class StatButton(Button):
    def __init__(self, statname, statdesc, **kwargs):
        Button.__init__(self, **kwargs)
        self.text = statname
        self.statdesc = statdesc
        self.bind(on_release = self.show_desc)
        self.size_hint = (0.5, mybtn_size_hint_y)
    
    def show_desc(self, btn):
        self.descpop = DescPopup(title = self.text, statdesc = self.statdesc)#content = Label(text = self.statdesc))
        self.descpop.open()

# Popup confirming deletion of stat.
# A stat can only have one parent BoxOfStats, and this happens there.
class DeletePopup(Popup):
    def __init__(self, caller, **kwargs):
        Popup.__init__(self, **kwargs)
        self.caller = caller
        statname = self.caller.parent.statname
        self.title = "Delete " + statname + "?"
        dplayout = BoxLayout()
        yesbtn = Button(text = "Yes", size_hint_y = 0.5)
        nobtn = Button(text = "No", size_hint_y = 0.5)
        yesbtn.bind(on_release = self.yesdel)
        nobtn.bind(on_release = self.nodel)
        dplayout.add_widget(yesbtn)
        dplayout.add_widget(nobtn)
        self.content = dplayout
    def yesdel(self, btn):
        self.caller.parent.parent.statlist.remove(self.caller.parent)
        self.caller.parent.parent.remove_widget(self.caller.parent)
        masterstatlist.remove(self.caller.parent)
        self.dismiss()
    def nodel(self, btn):
        self.dismiss()

# A button to delete the parent object.
class DeleteButton(Button):
    def __init__(self, **kwargs):
        Button.__init__(self, **kwargs)
        self.text = "X"
        self.background_normal = ""
        self.background_color = [0.7, 0, 0, 1]
        self.size_hint = (0.1, mybtn_size_hint_y)
        self.bind(on_release = self.delete_bar)
    def delete_bar(self, btn):
        self.delpop = DeletePopup(caller = self)
        self.delpop.open()

# Button to edit the parent object.
class EditButton(Button):
    def __init__(self, **kwargs):
        Button.__init__(self, **kwargs)
        self.text = "Edit"
        self.size_hint = (0.3, mybtn_size_hint_y)
        self.bind(on_release = self.edbtn_push)
    def edbtn_push(self, btn):
        self.parent.edit_obj()
        
# popup for editing a stat bar
class EditStatBarPopup(Popup):
    def __init__(self, caller, statname = "", statdesc = "", **kwargs):
        Popup.__init__(self, **kwargs)
        self.caller = caller
        self.layout = BoxLayout(orientation = "vertical")
        self.edlayout = GridLayout(cols = 2)
        
        # Rows for editing stat name and description
        self.edlayout.add_widget(Label(text = "Name", size_hint_x = edpop_left_col_size))
        self.statname_input = TextInput(text = statname, multiline = False)
        self.edlayout.add_widget(self.statname_input)
        
        self.edlayout.add_widget(Label(text = "Popup description", size_hint_x = edpop_left_col_size))
        self.statdesc_input = TextInput(text = statdesc)
        self.edlayout.add_widget(self.statdesc_input)
        
        self.layout.add_widget(self.edlayout)
        
        # Buttons for finishing or canceling stat editing
        self.donebtn_layout = BoxLayout(orientation = "horizontal", size_hint_y = 0.1)
        self.donebtn = Button(text = "Done")
        self.cancelbtn = Button(text = "Cancel")
        self.donebtn.bind(on_release = self.done_edit)
        self.cancelbtn.bind(on_release = self.cancel_edit)
        self.donebtn_layout.add_widget(self.donebtn)
        self.donebtn_layout.add_widget(self.cancelbtn)
        self.layout.add_widget(self.donebtn_layout)
        
        self.content = self.layout
        
    def done_edit(self, btn):
        self.caller.statname = sanitize_text(self.statname_input.text)
        self.caller.statdesc = sanitize_text(self.statdesc_input.text)
        self.caller.statbtn.text = self.caller.statname
        self.caller.statbtn.statdesc = self.caller.statdesc
        update_all_stat_text()
        self.dismiss()
    def cancel_edit(self, btn):
        self.dismiss()
    def on_open(self):
        # keep from changing pages while open
        global edit_window_open
        edit_window_open += 1
    def on_dismiss(self):
        global edit_window_open
        edit_window_open -= 1

# up and down buttons to reorder items on page        
class UpButton(Button):
    def __init__(self, **kwargs):
        Button.__init__(self, **kwargs)
        self.text = "^"
        self.size_hint = (0.1, mybtn_size_hint_y)
        self.bind(on_release = self.move_parent_up)
    def move_parent_up(self, btn):
        currindex = self.parent.parent.statlist.index(self.parent)
        if currindex == 1:
            neworder = [1, 0] + list(range(2, len(self.parent.parent.statlist)))
        if currindex > 1:
            neworder = list(range(currindex - 1)) + [currindex, currindex - 1] + \
                          list(range(currindex + 1, len(self.parent.parent.statlist)))
        if currindex > 0:
            self.parent.parent.statlist = [self.parent.parent.statlist[i] for i in neworder]
            self.parent.parent.redraw()
            
class DownButton(Button):
    def __init__(self, **kwargs):
        Button.__init__(self, **kwargs)
        self.text = "v"
        self.size_hint = (0.1, mybtn_size_hint_y)
        self.bind(on_release = self.move_parent_down)
    def move_parent_down(self, btn):
        currindex = self.parent.parent.statlist.index(self.parent)
        listlen = len(self.parent.parent.statlist)
        if currindex == listlen - 2:
            neworder = list(range(currindex)) + [currindex + 1, currindex]
        if currindex < listlen - 2:
            neworder = list(range(currindex)) + [currindex + 1, currindex] + list(range(currindex + 2, listlen))
        if currindex < listlen - 1:
            self.parent.parent.statlist = [self.parent.parent.statlist[i] for i in neworder]
            self.parent.parent.redraw()
  
# bar containing the button with the name of the stat.  Superclass for various types of stat.
class StatBar(BoxLayout):
    def __init__(self, statname, statdesc, calcavail = False, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = 0.2 # doesn't work?
        self.spacing = 3
        self.padding = 3
        
        self.statname = statname
        self.statdesc = statdesc
        self.calcavail = calcavail # is this stat available for calculation of other stats?
        self.statbtn = StatButton(statname = self.statname, statdesc = self.statdesc)
        self.upbtn = UpButton()
        self.downbtn = DownButton()
        self.delbtn = DeleteButton()
        self.editbtn = EditButton()
        
        self.add_widget(self.statbtn)
        self.add_widget(self.upbtn)
        self.add_widget(self.downbtn)
        self.add_widget(self.delbtn)
        self.add_widget(self.editbtn)
        
    def enter_edit_mode(self):
        self.add_widget(self.upbtn)
        self.add_widget(self.downbtn)
        self.add_widget(self.delbtn)
        self.add_widget(self.editbtn)
    def leave_edit_mode(self):
        self.remove_widget(self.upbtn)
        self.remove_widget(self.downbtn)
        self.remove_widget(self.delbtn)
        self.remove_widget(self.editbtn)
    def edit_obj(self):
        edpop = EditStatBarPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                 title = "Edit " + self.statname)
        edpop.open()
    def value_for_sum(self):
        return 0  # if there is no number associated with this stat, return zero
    def update_text_color(self):
        pass # this function does something if the stat bar has text printed on the background color
    def write_statbar_info(self, con):
        con.write("<statname>{}</statname>\n".format(self.statname))
        con.write("<statdesc>{}</statdesc>\n".format(self.statdesc))
        con.write("<calcavail>{}</calcavail>\n".format(self.calcavail))
        con.write("<statbtn.size_hint_x>{}</statbtn.size_hint_x>\n".format(self.statbtn.size_hint_x))
    def write_to_file(self, con):
        con.write("<StatBar>\n")
        self.write_statbar_info(con)
        con.write("</StatBar>\n\n")

# A checkbox to indicate number formatting (plus before number or not)
class NumFormatCheckbox(BoxLayout):
    def __init__(self, caller, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.caller = caller
        self.size_hint_y = 0.1
        self.add_widget(Label(text = "Include a '+' before positive numbers?", 
                              size_hint_x = 0.8))
        self.nfcheck = CheckBox()
        self.nfcheck.active = self.caller.caller.showplus
        self.add_widget(self.nfcheck)
        
# A checkbbox to indicate whether this stat is available for calculating others
class CalcAvailCheckbox(BoxLayout):
    def __init__(self, caller, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.caller = caller
        self.size_hint_y = 0.1
        self.add_widget(Label(text = "Make this stat available for calculating others?", 
                              size_hint_x = 0.8))
        self.cacheck = CheckBox()
        self.cacheck.active = self.caller.caller.calcavail
        self.add_widget(self.cacheck)
        
# popup for editing stat with a simple value
class EditStatBarSimplePopup(EditStatBarPopup):
    def __init__(self, statval = 0, **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        
        self.edlayout.add_widget(Label(text = "Value", size_hint_x = edpop_left_col_size))
        self.statval_input = TextInput(text = str(statval), input_filter = 'int')
        self.edlayout.add_widget(self.statval_input)
        
        self.nfcheckbar = NumFormatCheckbox(caller = self)
        self.layout.add_widget(self.nfcheckbar, index = 1)
        
        self.cacheckbar = CalcAvailCheckbox(caller = self)
        self.layout.add_widget(self.cacheckbar, index = 1)
        
    def done_edit(self, btn):
        # update the stored and printed value
        self.caller.statval = int(self.statval_input.text)
        # update whether the '+' should be before the number
        self.caller.showplus = self.nfcheckbar.nfcheck.active
        # update whether this stat is available for calculations
        self.caller.calcavail = self.cacheckbar.cacheck.active
        # update text printed on label - is done by update_all_stat_text within EditStatBarPopup
        # do all other updates
        EditStatBarPopup.done_edit(self, btn)
        
# bar for a stat with a simple value
class StatBarSimple(StatBar):
    def __init__(self, statval, showplus = False, **kwargs):
        StatBar.__init__(self, **kwargs)
        self.statval = int(statval)
        self.showplus = showplus # show plus sign (for roll mods)?
        self.statlbl = Label(text = self.value_text(), size_hint_y = mybtn_size_hint_y, size_hint_x = 0.5)
        nchild = len(self.children)
        self.add_widget(self.statlbl, index = nchild - 1)
    def edit_obj(self):
        edpop = EditStatBarSimplePopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                       statval = self.statval, title = "Edit " + self.statname)
        edpop.open()
    def value_for_sum(self):
        return self.statval
    def value_text(self):
        if self.showplus:
            stattext = '{:+d}'.format(self.statval)
        else:
            stattext = str(self.statval)
        return stattext
    def update_button_text(self):
        self.statlbl.text = self.value_text()
    def update_text_color(self):
        if self.parent.red_bg + self.parent.green_bg + self.parent.blue_bg > 1.4:
            self.statlbl.color = [0,0,0,1] # black on light background
        else:
            self.statlbl.color = [1,1,1,1] # white on dark background
    def write_to_file(self, con):
        con.write("<StatBarSimple>\n")
        self.write_statbar_info(con)
        con.write("<statval>{}</statval>\n".format(self.statval))
        con.write("<showplus>{}</showplus>\n".format(self.showplus))
        con.write("</StatBarSimple>\n\n")

# popup for adding an existing stat to a sum
class AddExistingStatPopup(Popup):
    def __init__(self, caller, **kwargs):
        Popup.__init__(self, **kwargs)
        self.caller = caller
        self.title = "Add existing stat to sum"
        self.layout = BoxLayout(orientation = "vertical")
        
        # one button for each stat that could be added
        self.statoptions = find_stats_for_calc()
        self.addbtns = [Button(text = s.statname + " " + s.value_text()) for s in self.statoptions]
        [ab.bind(on_release = self.add_stat) for ab in self.addbtns]
        [self.layout.add_widget(ab) for ab in self.addbtns]
        
        cancelbtn = Button(text = "Cancel")
        cancelbtn.bind(on_release = self.dismiss)
        self.layout.add_widget(cancelbtn)
        
        self.add_widget(self.layout)
    def add_stat(self, btn):
        i = self.addbtns.index(btn) # index of stat on this screen
        j = len(self.caller.statlist_existing) # index of stat on parent screen
        st = self.statoptions[i] # the stat to be added
        self.caller.statlist_existing.append(st) # list to ultimately be passed down and kept
        # For display in parent window
        self.caller.names.append(Label(text = st.statname))
        self.caller.vals.append(Label(text = st.value_text()))
        self.caller.delbtns.append(Button(text = "X"))
        self.caller.delbtns[j].bind(on_release = self.caller.delete_component)
        self.caller.grid.add_widget(self.caller.names[j])
        self.caller.grid.add_widget(self.caller.vals[j])
        self.caller.grid.add_widget(self.caller.delbtns[j])
        self.dismiss()
        
# popup to show components of a sum and allow editing
class EditStatlistPopup(Popup):
    def __init__(self, caller, statlist_existing, **kwargs):
        Popup.__init__(self, **kwargs)
        self.caller = caller
        self.statlist_existing = statlist_existing
        self.title = "Edit " + self.caller.caller.statname + " components"
        
        # Grid of stats that were created elsewhere
        self.grid = GridLayout(cols = 3)
        self.names = [Label(text = s.statname) for s in self.statlist_existing]
        self.vals = [Label(text = s.value_text()) for s in self.statlist_existing]
        self.delbtns = [Button(text = "X") for s in self.statlist_existing]
        for i in range(len(self.statlist_existing)): 
            self.grid.add_widget(self.names[i])
            self.grid.add_widget(self.vals[i])
            self.delbtns[i].bind(on_release = self.delete_component)
            self.grid.add_widget(self.delbtns[i])
         
        self.donebar = BoxLayout()
        self.donebar.size_hint_y = 0.1
        self.donebtn = Button(text = "Done", size_hint_y = None, height = myminheight)
        self.cancelbtn = Button(text = "Cancel changes to list of existing stats", size_hint_y = None, height = myminheight)
        self.donebtn.bind(on_release = self.done_edit)
        self.cancelbtn.bind(on_release = self.dismiss)
        self.donebar.add_widget(self.donebtn)
        self.donebar.add_widget(self.cancelbtn)
        
        self.addexistbtn = Button(text = "Add existing stat", size_hint_y = None, height = myminheight)
        self.addexistbtn.bind(on_release = self.add_component_existing)
        
        self.layout = BoxLayout(orientation = "vertical")
        self.layout.add_widget(self.caller.caller.childstats) # contains component stats specific to this stat
        self.layout.add_widget(self.addexistbtn)
        self.layout.add_widget(self.grid)
        self.layout.add_widget(self.donebar)
        self.content = self.layout
    def delete_component(self, btn):
        i = self.delbtns.index(btn) # index of stat to remove
        self.statlist_existing.pop(i)
        # remove everything on that row of the grid
        self.grid.remove_widget(self.names[i])
        self.grid.remove_widget(self.vals[i])
        self.grid.remove_widget(self.delbtns[i])
        self.names.pop(i)
        self.vals.pop(i)
        self.delbtns.pop(i)
    def add_component_existing(self, btn):
        self.adpopex = AddExistingStatPopup(caller = self)
        self.adpopex.open()
    def done_edit(self, btn):
        self.caller.statlist_existing = self.statlist_existing # pass statlist to parent edit window
        self.caller.valbtn.text = self.value_text() # update popup button value
        self.dismiss()
    def value_text(self):
        # total value for current version of statlist
        valtot = sum([s.value_for_sum() for s in self.statlist_existing + self.caller.caller.childstats.statlist])
        if self.caller.caller.showplus:
            stattext = '{:+d}'.format(valtot)
        else:
            stattext = str(valtot)
        return stattext
    def on_dismiss(self):
        self.layout.remove_widget(self.caller.caller.childstats)
        
# popup to edit a statistic that is a sum of other statistics
class EditStatBarSumPopup(EditStatBarPopup):
    def __init__(self, statlist_existing = [], **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        
        self.statlist_existing = statlist_existing
        self.edlayout.add_widget(Label(text = "Value", size_hint_x = edpop_left_col_size))
        self.valbtn = Button(text = self.caller.value_text(), size_hint_y = mybtn_size_hint_y)
        self.valbtn.bind(on_release = self.edit_sum)
        self.edlayout.add_widget(self.valbtn)
        
        self.nfcheckbar = NumFormatCheckbox(caller = self)
        self.layout.add_widget(self.nfcheckbar, index = 1)
        
        self.cacheckbar = CalcAvailCheckbox(caller = self)
        self.layout.add_widget(self.cacheckbar, index = 1)
        
    def edit_sum(self, btn):
        self.edslpop = EditStatlistPopup(caller = self, statlist_existing = copy(self.statlist_existing))
        self.edslpop.open()
    def done_edit(self, btn):
        # update whether the '+' should be before the number
        self.caller.showplus = self.nfcheckbar.nfcheck.active
        # update whether this stat is available for calculations
        self.caller.calcavail = self.cacheckbar.cacheck.active
        # pass on the statlist
        self.caller.statlist_existing = self.statlist_existing
        # update text printed on label - done by update_all_stat_text within EditStatBarPopup
        # do all other updates
        EditStatBarPopup.done_edit(self, btn)
        
# bar for a stat with a calculated value
class StatBarSum(StatBar):
    def __init__(self, statlist_existing = [], statlist_new = [], showplus = False, **kwargs):
        StatBar.__init__(self, **kwargs)
        self.statlist_existing = statlist_existing
        self.showplus = showplus
        # BoxLayout containing the stats that were created within this stat.
        # Not plotted here, but plotted in the editing popup.
        self.childstats = BoxOfStats(statlist = statlist_new, numbersOnly = True)
        self.childstats.remove_widget(self.childstats.leave_edit_btn)
        # Add these substats specific to this stat to the master list, since they should be brand new
        masterstatlist.extend(statlist_new)
        
        # Add label showing the numeric value (total) for this statistic
        self.statlbl = Button(text = self.value_text(), size_hint_y = mybtn_size_hint_y, size_hint_x = 0.5)
        self.statlbl.bind(on_release = self.show_components)
        nchild = len(self.children)
        self.add_widget(self.statlbl, index = nchild - 1)
        
    def show_components(self, btn):
        "Function to make a popup showing components of the sum (no editing)"
        self.sumpop = Popup(title = "Components of " + self.statname)
        self.sumpop.layout = BoxLayout(orientation = "vertical")
        self.sumpop.grid = GridLayout(cols = 2)
        for s in self.statlist_existing + self.childstats.statlist:
            self.sumpop.grid.add_widget(Label(text = s.statname))
            self.sumpop.grid.add_widget(Label(text = s.value_text()))
        self.sumpop.layout.add_widget(self.sumpop.grid)
        self.sumpop.closebtn = Button(text = "Close", size_hint_y = None, height = myminheight)
        self.sumpop.closebtn.bind(on_release = self.sumpop.dismiss)
        self.sumpop.layout.add_widget(self.sumpop.closebtn)
        self.sumpop.content = self.sumpop.layout
        self.sumpop.open()
    def edit_obj(self):
        edpop = EditStatBarSumPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                    statlist_existing = copy(self.statlist_existing), title = "Edit " + self.statname)
        edpop.open()
    def value_for_sum(self):
        return sum([s.value_for_sum() for s in self.statlist_existing]) + \
          sum([s.value_for_sum() for s in self.childstats.statlist])
    def value_text(self):
        if self.showplus:
            stattext = '{:+d}'.format(self.value_for_sum())
        else:
            stattext = str(self.value_for_sum())
        return stattext
    def update_button_text(self):
        self.statlbl.text = self.value_text()
    def add_existing_stat(self, stat):
        self.statlist_existing.append(stat)
    def write_statbarsum(self, con):
        self.write_statbar_info(con)
        se_index = [str(masterstatlist.index(s)) for s in self.statlist_existing]
        sn_index = [str(masterstatlist.index(s)) for s in self.childstats.statlist]
        con.write("<statlist_existing>{}</statlist_existing>\n".format(",".join(se_index)))
        con.write("<childstats.statlist>{}</childstats.statlist>\n".format(",".join(sn_index)))
        con.write("<showplus>{}</showplus>\n".format(self.showplus))
    def write_to_file(self, con):
        con.write("<StatBarSum>\n")
        self.write_statbarsum(con)
        con.write("</StatBarSum>\n\n")

# popup to edit D&D ability
class EditDDAbilityBarPopup(EditStatBarSumPopup):
    def __init__(self, **kwargs):
        EditStatBarSumPopup.__init__(self, **kwargs)
        # eliminate check box for having the plus or not
        self.layout.remove_widget(self.nfcheckbar)
        
# bar with D&D ability and modifier
class DDAbilityBar(StatBarSum):
    def __init__(self, **kwargs):
        StatBarSum.__init__(self, **kwargs)
        self.calcavail = True # generally want D&D roll mods for calculations
    def edit_obj(self):
        edpop = EditDDAbilityBarPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                      title = "Edit " + self.statname, statlist_existing = self.statlist_existing)
        edpop.open()
    def value_for_sum(self):
        score = sum([s.value_for_sum() for s in self.statlist_existing + self.childstats.statlist])
        return (score - 10) // 2
    def value_text(self):
        # text for label has ability followed by modifier
        score = sum([s.value_for_sum() for s in self.statlist_existing + self.childstats.statlist])
        return "{} ({:+d})".format(score, self.value_for_sum())
    def write_to_file(self, con):
        con.write("<DDAbilityBar>\n")
        self.write_statbarsum(con)
        con.write("</DDAbilityBar>\n\n")

# popup for changing the stat used for StatBarFraction
class SelectStatPopup(AddExistingStatPopup):
    def __init__(self, **kwargs):
        AddExistingStatPopup.__init__(self, **kwargs)
    def add_stat(self, btn):
        i = self.addbtns.index(btn) # index of stat on this screen
        st = self.statoptions[i] # the stat to be added
        # pass the stat to the edit window
        self.caller.stat_to_div = st
        # update the button label in the edit window
        self.caller.stat_to_div_btn.text = self.caller.stat_to_div.statname + " " + self.caller.stat_to_div.value_text()
        self.dismiss()
        
# popup to edit a bar that is a fraction of another stat
class EditStatBarFractionPopup(EditStatBarPopup):
    def __init__(self, stat_to_div, divisor, rounddown, **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        self.stat_to_div = stat_to_div
        self.divisor = divisor
        self.rounddown = rounddown
        
        self.edlayout.add_widget(Label(text = "Stat to divide", size_hint_x = edpop_left_col_size))
        stat_to_div_text = "" if stat_to_div == None else self.stat_to_div.statname + ": " + self.stat_to_div.value_text()
        self.stat_to_div_btn = Button(text = stat_to_div_text)
        self.stat_to_div_btn.bind(on_release = self.pick_stat)
        self.edlayout.add_widget(self.stat_to_div_btn)
        
        self.edlayout.add_widget(Label(text = "Divide by", size_hint_x = edpop_left_col_size))
        self.divisor_input = TextInput(text = str(self.divisor), input_filter = 'int')
        self.edlayout.add_widget(self.divisor_input)
        
        # bar with radio buttons for rounding up or down
        self.rounddown_radio = CheckBox(active = self.rounddown, group = "round")
        self.roundup_radio = CheckBox(active = not self.rounddown, group = "round")
        self.roundbar = BoxLayout()
        self.roundbar.add_widget(Label(text = "Round down:"))
        self.roundbar.add_widget(self.rounddown_radio)
        self.roundbar.add_widget(Label(text = "Round up:"))
        self.roundbar.add_widget(self.roundup_radio)
        self.roundbar.size_hint_y = 0.1
        self.layout.add_widget(self.roundbar, index = 1)
        
        self.nfcheckbar = NumFormatCheckbox(caller = self)
        self.layout.add_widget(self.nfcheckbar, index = 1)
        
        self.cacheckbar = CalcAvailCheckbox(caller = self)
        self.layout.add_widget(self.cacheckbar, index = 1)
    def pick_stat(self, btn):
        adpop = SelectStatPopup(caller = self)
        adpop.open()
    def done_edit(self, btn):
        # update the stat used
        self.caller.stat_to_div = self.stat_to_div
        # update the divisor
        try:
            self.caller.divisor = int(self.divisor_input.text)
        except ValueError: # for if there is a blank where an int expected
            self.caller.divisor = 1
        # update whether to round up or down
        self.caller.rounddown = self.rounddown_radio.active
        # update whether the '+' should be before the number
        self.caller.showplus = self.nfcheckbar.nfcheck.active
        # update whether this stat is available for calculations
        self.caller.calcavail = self.cacheckbar.cacheck.active
        # do all other updates
        EditStatBarPopup.done_edit(self, btn)
        
# bar with fraction of another stat
class StatBarFraction(StatBar):
    def __init__(self, stat_to_div = None, divisor = 2, rounddown = True, showplus = False, **kwargs):
        StatBar.__init__(self, **kwargs)
        
        self.stat_to_div = stat_to_div
        self.divisor = divisor
        self.rounddown = rounddown
        self.showplus = showplus
        
        self.statlbl = Button(text = self.value_text(), size_hint_x = 0.5)
        self.statlbl.bind(on_release = self.show_components)
        self.add_widget(self.statlbl, index = len(self.children) - 1)
        
    def show_components(self, btn):
        comp_popup = Popup(title = "Calculation of " + self.statname)
        comp_popup.content = Label(text = self.stat_to_div.statname + ": " + self.stat_to_div.value_text() + \
                                   "\n\ndivided by " + str(self.divisor) + "\n\nrounded " + \
                                   ("down" if self.rounddown else "up"))
        comp_popup.bind(on_touch_up = comp_popup.dismiss)
        comp_popup.open()
    def value_for_sum(self):
        if self.stat_to_div == None:
            return 0
        else:
            numerator = self.stat_to_div.value_for_sum()
            val =  numerator // self.divisor
            if not self.rounddown and numerator % self.divisor > 0:
                val += 1
            return val
    def value_text(self):
        if self.showplus:
            stattext = '{:+d}'.format(self.value_for_sum())
        else:
            stattext = str(self.value_for_sum())
        return stattext
    def update_button_text(self):
        self.statlbl.text = self.value_text()
    def edit_obj(self):
        edpop = EditStatBarFractionPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                         stat_to_div = self.stat_to_div, divisor = self.divisor,
                                         title = "Edit " + self.statname, rounddown = self.rounddown)
        edpop.open()
    def write_to_file(self, con):
        con.write("<StatBarFraction>\n")
        self.write_statbar_info(con)
        statindex = None if self.stat_to_div == None else masterstatlist.index(self.stat_to_div)
        con.write("<stat_to_div>{}</stat_to_div>\n".format(statindex))
        con.write("<divisor>{}</divisor>\n".format(self.divisor))
        con.write("<rounddown>{}</rounddown>\n".format(self.rounddown))
        con.write("<showplus>{}</showplus>\n".format(self.showplus))
        con.write("</StatBarFraction>\n\n")
        
# popup for editing stat bar with text box
class EditStatBarTextPopup(EditStatBarPopup):
    def __init__(self, stattext, **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        
        self.edlayout.add_widget(Label(text = "Text next to button", size_hint_x = edpop_left_col_size))
        self.stattext_input = TextInput(text = stattext)
        self.edlayout.add_widget(self.stattext_input)
    def done_edit(self, btn):
        # update the stored and printed value for text
        self.caller.stattext = sanitize_text(self.stattext_input.text)
        self.caller.statlbl.text = self.caller.stattext
        # do all other updates
        EditStatBarPopup.done_edit(self, btn)
    
# bar with stat button and freestyle text
class StatBarText(StatBar):
    def __init__(self, stattext, **kwargs):
        StatBar.__init__(self, **kwargs)
        self.stattext = stattext
        self.statlbl = Label(text = self.stattext, size_hint_y = mybtn_size_hint_y, size_hint_x = 0.5)
        nchild = len(self.children)
        self.add_widget(self.statlbl, index = nchild - 1)
    def edit_obj(self):
        edpop = EditStatBarTextPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                     stattext = self.stattext, title = "Edit " + self.statname)
        edpop.open()
    def update_text_color(self): # make text white or black as appropriate.
        StatBarSimple.update_text_color(self)
    def write_to_file(self, con):
        con.write("<StatBarText>\n")
        self.write_statbar_info(con)
        con.write("<stattext>{}</stattext>\n".format(self.stattext))
        con.write("</StatBarText>\n\n")
        
# popup to edit a counter for hit points etc.
class EditStatBarCounterPopup(EditStatBarPopup):
    def __init__(self, defaultval, **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        self.edlayout.add_widget(Label(text = "Default value", size_hint_x = edpop_left_col_size))
        self.val_input = TextInput(text = str(defaultval), input_filter = 'int')
        self.edlayout.add_widget(self.val_input)
        
        self.cacheckbar = CalcAvailCheckbox(caller = self)
        self.layout.add_widget(self.cacheckbar, index = 1)
    def done_edit(self, btn):
        # update the stored and printed value
        self.caller.defaultval = int(self.val_input.text)
        self.caller.currentval = self.caller.defaultval # reset the current value to the new default
        self.caller.update_button_text()
        # update whether this stat is available for calculations
        self.caller.calcavail = self.cacheckbar.cacheck.active
        # Do all other updates
        EditStatBarPopup.done_edit(self, btn)

# bar with counter for hit points etc.
class StatBarCounter(StatBar):
    def __init__(self, defaultval, **kwargs):
        StatBar.__init__(self, **kwargs)
        self.defaultval = defaultval
        self.currentval = self.defaultval
        
        self.statlbl = Label(text = str(self.currentval), size_hint_y = mybtn_size_hint_y, size_hint_x = 0.3)
        nchild = len(self.children)
        self.add_widget(self.statlbl, index = nchild - 1)
        
        self.incbtn = Button(text = "+", size_hint_y = mybtn_size_hint_y, size_hint_x = 0.05)
        self.incbtn.bind(on_release = self.increase_value)
        self.add_widget(self.incbtn, index = nchild - 1)
        self.decbtn = Button(text = "-", size_hint_y = mybtn_size_hint_y, size_hint_x = 0.05)
        self.decbtn.bind(on_release = self.decrease_value)
        self.add_widget(self.decbtn, index = nchild - 1)
        self.defbtn = Button(text = "Reset", size_hint_y = mybtn_size_hint_y, size_hint_x = 0.1)
        self.defbtn.bind(on_release = self.set_to_default)
        self.add_widget(self.defbtn, index = nchild - 1)
        
    def increase_value(self, btn):
        self.currentval += 1
        self.update_button_text()
        if self.calcavail:
            update_all_stat_text()
    def decrease_value(self, btn):
        self.currentval -= 1
        self.update_button_text()
        if self.calcavail:
            update_all_stat_text()
    def set_to_default(self, btn):
        self.currentval = self.defaultval
        self.update_button_text()
        if self.calcavail:
            update_all_stat_text()
    def edit_obj(self):
        edpop = EditStatBarCounterPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                        defaultval = self.defaultval, title = "Edit " + self.statname)
        edpop.open()
    def value_text(self):
        return str(self.currentval)
    def update_button_text(self):
        self.statlbl.text = self.value_text()
    def value_for_sum(self):
        return self.currentval
    def update_text_color(self): # make text white or black as appropriate.
        StatBarSimple.update_text_color(self)
    def write_to_file(self, con):
        con.write("<StatBarCounter>\n")
        self.write_statbar_info(con)
        con.write("<defaultval>{}</defaultval>\n".format(self.defaultval))
        con.write("<currentval>{}</currentval>\n".format(self.currentval))
        con.write("</StatBarCounter>\n\n")

# popup editor for bar with two buttons
class EditStatBarTwoButtonsPopup(EditStatBarPopup):
    def __init__(self, statname2, statdesc2, **kwargs):
        EditStatBarPopup.__init__(self, **kwargs)
        self.statname2 = statname2
        self.statdesc2 = statdesc2
        
        self.edlayout.add_widget(Label(text = "Name 2", size_hint_x = edpop_left_col_size))
        self.statname2_input = TextInput(text = statname2, multiline = False)
        self.edlayout.add_widget(self.statname2_input)
        
        self.edlayout.add_widget(Label(text = "Popup description 2", size_hint_x = edpop_left_col_size))
        self.statdesc2_input = TextInput(text = statdesc2)
        self.edlayout.add_widget(self.statdesc2_input)
        
    def done_edit(self, btn):
        # update name and description for second stat
        self.caller.statname2 = sanitize_text(self.statname2_input.text)
        self.caller.statbtn2.text = self.caller.statname2
        self.caller.statdesc2 = sanitize_text(self.statdesc2_input.text)
        self.caller.statbtn2.statdesc = self.caller.statdesc2
        # do all other updates
        EditStatBarPopup.done_edit(self, btn)
        
# Bar with two buttons for popup text
class StatBarTwoButtons(StatBar):
    def __init__(self, statname2, statdesc2, **kwargs):
        StatBar.__init__(self, **kwargs)
        self.statname2 = statname2
        self.statdesc2 = statdesc2
        
        self.statbtn2 = StatButton(statname = self.statname2, statdesc = self.statdesc2)
        self.add_widget(self.statbtn2, index = len(self.children) - 1)
    def edit_obj(self):
        edpop = EditStatBarTwoButtonsPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                           statname2 = self.statname2, statdesc2 = self.statdesc2, 
                                           title = "Edit row of buttons")
        edpop.open()
    def write_to_file(self, con):
        con.write("<StatBarTwoButtons>\n")
        self.write_statbar_info(con)
        con.write("<statname2>{}</statname2>\n".format(self.statname2))
        con.write("<statdesc2>{}</statdesc2>\n".format(self.statdesc2))
        con.write("</StatBarTwoButtons>\n\n")
 
# popup editor for bar with two buttons
class EditStatBarThreeButtonsPopup(EditStatBarTwoButtonsPopup):
    def __init__(self, statname3, statdesc3, **kwargs):
        EditStatBarTwoButtonsPopup.__init__(self, **kwargs)
        self.statname3 = statname3
        self.statdesc3 = statdesc3
        
        self.edlayout.add_widget(Label(text = "Name 3", size_hint_x = edpop_left_col_size))
        self.statname3_input = TextInput(text = statname3, multiline = False)
        self.edlayout.add_widget(self.statname3_input)
        
        self.edlayout.add_widget(Label(text = "Popup description 3", size_hint_x = edpop_left_col_size))
        self.statdesc3_input = TextInput(text = statdesc3)
        self.edlayout.add_widget(self.statdesc3_input)
        
    def done_edit(self, btn):
        # update name and description for second stat
        self.caller.statname3 = sanitize_text(self.statname3_input.text)
        self.caller.statbtn3.text = self.caller.statname3
        self.caller.statdesc3 = sanitize_text(self.statdesc3_input.text)
        self.caller.statbtn3.statdesc = self.caller.statdesc3
        # do all other updates
        EditStatBarTwoButtonsPopup.done_edit(self, btn)
 
# Bar with three buttons for popup text
class StatBarThreeButtons(StatBarTwoButtons):
    def __init__(self, statname3, statdesc3, **kwargs):
        StatBarTwoButtons.__init__(self, **kwargs)
        self.statname3 = statname3
        self.statdesc3 = statdesc3
        
        self.statbtn3 = StatButton(statname = self.statname3, statdesc = self.statdesc3)
        self.add_widget(self.statbtn3, index = len(self.children) - 2)
    def edit_obj(self):
        edpop = EditStatBarThreeButtonsPopup(caller = self, statname = self.statname, statdesc = self.statdesc,
                                             statname2 = self.statname2, statdesc2 = self.statdesc2,
                                             statname3 = self.statname3, statdesc3 = self.statdesc3,
                                             title = "Edit row of buttons")
        edpop.open()
    def write_to_file(self, con):
        con.write("<StatBarThreeButtons>\n")
        self.write_statbar_info(con)
        con.write("<statname2>{}</statname2>\n".format(self.statname2))
        con.write("<statdesc2>{}</statdesc2>\n".format(self.statdesc2))
        con.write("<statname3>{}</statname3>\n".format(self.statname3))
        con.write("<statdesc3>{}</statdesc3>\n".format(self.statdesc3))
        con.write("</StatBarThreeButtons>\n\n")

# popup dialog for adding a new item to the sheet        
class AddStatPopup(Popup):
    def __init__(self, caller, **kwargs):
        Popup.__init__(self, **kwargs)
        self.title = "Add new item to character sheet"
        self.layout = BoxLayout(orientation = "vertical")
        self.caller = caller
        
        self.stat_simple_btn = Button(text = "Add simple numeric stat")
        self.stat_simple_btn.bind(on_release = self.add_stat_simple)
        self.layout.add_widget(self.stat_simple_btn)
        
        self.stat_sum_btn = Button(text = "Add stat from sum")
        self.stat_sum_btn.bind(on_release = self.add_stat_sum)
        self.layout.add_widget(self.stat_sum_btn)
        
        self.dd_ability_btn = Button(text = "Add D&D ability score")
        self.dd_ability_btn.bind(on_release = self.add_dd_ability)
        self.layout.add_widget(self.dd_ability_btn)
        
        self.counter_btn = Button(text = "Add counter")
        self.counter_btn.bind(on_release = self.add_counter)
        self.layout.add_widget(self.counter_btn)
        
        self.fraction_btn = Button(text = "Add stat that is a fraction of another stat")
        self.fraction_btn.bind(on_release = self.add_fraction)
        self.layout.add_widget(self.fraction_btn)
        
        # non-numeric stuff to add
        if not self.caller.numbersOnly:
            self.stat_text_btn = Button(text = "Add button with text next to it")
            self.stat_text_btn.bind(on_release = self.add_stat_text)
            self.layout.add_widget(self.stat_text_btn)
            
            self.bigbutton_btn = Button(text = "Just a big wide button")
            self.bigbutton_btn.bind(on_release = self.add_bigbutton)
            self.layout.add_widget(self.bigbutton_btn)
            
            self.twobuttons_btn = Button(text = "Row of two buttons")
            self.twobuttons_btn.bind(on_release = self.add_twobuttons)
            self.layout.add_widget(self.twobuttons_btn)
            
            self.threebuttons_btn = Button(text = "Row of three buttons")
            self.threebuttons_btn.bind(on_release = self.add_threebuttons)
            self.layout.add_widget(self.threebuttons_btn)
        
        self.cancelbtn = Button(text = "Cancel")
        self.cancelbtn.bind(on_release = self.dismiss)
        self.layout.add_widget(self.cancelbtn)
        
        self.content = self.layout
    def add_stat_simple(self, btn):
        newstat = StatBarSimple(statname = "", statdesc = "", statval = 0)
        self.finish_adding_stats(newstat)
    def add_stat_sum(self, btn):
        newstat = StatBarSum(statname = "", statdesc = "", statlist_existing = [], statlist_new = [])
        self.finish_adding_stats(newstat)
    def add_dd_ability(self, btn):
        newstat = DDAbilityBar(statname = "", 
                               statdesc = "Ability score is listed first, followed by the roll modifier in parentheses.",
                               statlist_existing = [], 
                               statlist_new = [StatBarSimple(statname = "Base score", 
                                                             statdesc = "Score assigned at level 1 before racial modifiers",
                                                             statval = 10)])
        self.finish_adding_stats(newstat)
    def add_counter(self, btn):
        newstat = StatBarCounter(statname = "", statdesc = "", defaultval = 0)
        self.finish_adding_stats(newstat)
    def add_fraction(self, btn):
        newstat = StatBarFraction(statname = "", statdesc = "")
        self.finish_adding_stats(newstat)
    def add_stat_text(self, btn):
        newstat = StatBarText(statname = "", statdesc = "", stattext = "")
        self.finish_adding_stats(newstat)
    def add_bigbutton(self, btn):
        newstat = StatBar(statname = "", statdesc = "")
        newstat.statbtn.size_hint_x = 1
        self.finish_adding_stats(newstat)
    def add_twobuttons(self, btn):
        newstat = StatBarTwoButtons(statname = "", statdesc = "", statname2 = "", statdesc2 = "")
        self.finish_adding_stats(newstat)
    def add_threebuttons(self, btn):
        newstat = StatBarThreeButtons(statname = "", statdesc = "", statname2 = "", statdesc2 = "",
                                      statname3 = "", statdesc3 = "")
        self.finish_adding_stats(newstat)
    def finish_adding_stats(self, stat):
        stat.edit_obj()
        self.caller.statlist.append(stat)
        self.caller.add_widget(stat)
        masterstatlist.append(stat)
        self.dismiss()

# Box for entering a color
class RGBbox(BoxLayout):
    def __init__(self, r, g, b, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.entrygrid = GridLayout(cols = 2)
        self.r = r
        self.g = g
        self.b = b
        
        self.entrygrid.add_widget(Label(text = "Red (0-255)"))
        self.r_box = TextInput(text = str(int(r*255)), input_filter = "int")
        self.r_box.bind(text = self.get_color_from_text)
        self.entrygrid.add_widget(self.r_box)
        
        self.entrygrid.add_widget(Label(text = "Green (0-255)"))
        self.g_box = TextInput(text = str(int(g*255)), input_filter = "int")
        self.g_box.bind(text = self.get_color_from_text)
        self.entrygrid.add_widget(self.g_box)
        
        self.entrygrid.add_widget(Label(text = "Blue (0-255)"))
        self.b_box = TextInput(text = str(int(b*255)), input_filter = "int")
        self.b_box.bind(text = self.get_color_from_text)
        self.entrygrid.add_widget(self.b_box)
        
        self.add_widget(self.entrygrid)
        
        self.col_disp_btn = Button(background_normal = "", background_color = [self.r, self.g, self.b, 1])
        self.add_widget(self.col_disp_btn)
    def update_btn_color(self):
        self.col_disp_btn.background_color = [self.r, self.g, self.b, 1]
    def get_color_from_text(self, instance, value):
        if value != "":
            self.r = int(self.r_box.text)/255
            self.g = int(self.g_box.text)/255
            self.b = int(self.b_box.text)/255
            self.update_btn_color()
        
# Popup for editing color of a BoxOfStats
class EditColorPopup(Popup):
    def __init__(self, caller, currentcol, **kwargs):
        Popup.__init__(self, **kwargs)
        self.caller = caller
        self.currentcol = currentcol
        self.title = "Edit background color" # add text color later?
        self.layout = BoxLayout(orientation = "vertical")
        
        self.bgbox = RGBbox(r = currentcol[0], g = currentcol[1], b = currentcol[2])
        self.layout.add_widget(self.bgbox)
        
        self.donebtn = Button(text = "Done", height = myminheight, size_hint_y = None)
        self.donebtn.bind(on_release = self.done_edit)
        self.layout.add_widget(self.donebtn)
        
        self.cancelbtn = Button(text = "Cancel", height = myminheight, size_hint_y = None)
        self.cancelbtn.bind(on_release = self.dismiss)
        self.layout.add_widget(self.cancelbtn)
        
        self.add_widget(self.layout)
    def done_edit(self, btn):
        # update background colors
        self.caller.red_bg = self.bgbox.r
        self.caller.green_bg = self.bgbox.g
        self.caller.blue_bg = self.bgbox.b
        [st.update_text_color() for st in self.caller.statlist]
        self.dismiss()
    def on_open(self):
        # keep from changing pages while open
        global edit_window_open
        edit_window_open += 1
    def on_dismiss(self):
        global edit_window_open
        edit_window_open -= 1
        
# A boxlayout that has a group of stats.
class BoxOfStats(BoxLayout):
    red_bg = NumericProperty(0)
    green_bg = NumericProperty(0.5)
    blue_bg = NumericProperty(0.55)
    def __init__(self, statlist, numbersOnly = False, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.orientation = "vertical"
        self.statlist = statlist
        self.numbersOnly = numbersOnly # can this box contain non-numeric stat bars
        
        self.add_stat_btn = Button(text = "Add new item", height = myminheight, size_hint_y = None)
        self.add_stat_btn.bind(on_release = self.add_stat)
        self.add_widget(self.add_stat_btn)
        
        self.edit_color_btn = Button(text = "Edit color", height = myminheight, size_hint_y = None)
        self.edit_color_btn.bind(on_release = self.edit_color)
        self.add_widget(self.edit_color_btn)
        
        self.leave_edit_btn = Button(text = "Leave edit mode", height = myminheight, size_hint_y = None)
        self.leave_edit_btn.bind(on_release = self.leave_edit_mode)
        self.add_widget(self.leave_edit_btn)
        
        self.enter_edit_btn = Button(text = "Enter edit mode", height = myminheight, size_hint_y = None)
        self.enter_edit_btn.bind(on_release = self.enter_edit_mode)
        
        # draw all stats
        [self.add_widget(s) for s in self.statlist]
        
    def add_stat(self, btn):
        self.statpop = AddStatPopup(caller = self)
        self.statpop.open()
    def redraw(self):
        for s in self.statlist:
            self.remove_widget(s)
        for s in self.statlist:
            self.add_widget(s)
    def leave_edit_mode(self, btn):
        [s.leave_edit_mode() for s in self.statlist]
        self.remove_widget(self.add_stat_btn)
        self.remove_widget(self.edit_color_btn)
        self.remove_widget(self.leave_edit_btn)
        self.add_widget(self.enter_edit_btn, index = len(self.statlist))
    def enter_edit_mode(self, btn):
        [s.enter_edit_mode() for s in self.statlist]
        self.add_widget(self.add_stat_btn, index = len(self.statlist))
        self.add_widget(self.edit_color_btn, index = len(self.statlist))
        self.add_widget(self.leave_edit_btn, index = len(self.statlist))
        self.remove_widget(self.enter_edit_btn)
    def edit_color(self, btn):
        self.colpop = EditColorPopup(caller = self, currentcol = [self.red_bg, self.green_bg, self.blue_bg])
        self.colpop.open()
    def write_to_file(self, con):
        con.write("<BoxOfStats>\n")
        con.write("<red_bg>{}</red_bg>\n".format(self.red_bg))
        con.write("<green_bg>{}</green_bg>\n".format(self.green_bg))
        con.write("<blue_bg>{}</blue_bg>\n".format(self.blue_bg))
        statindex = [str(masterstatlist.index(s)) for s in self.statlist]
        con.write("<statlist>{}</statlist>\n".format(",".join(statindex)))
        con.write("</BoxOfStats>\n\n")
        
# popup for saving sheet
class SavePopup(Popup):
    def __init__(self, caller, **kwargs):
        Popup.__init__(self, **kwargs)
        self.title = "Save character sheet"
        self.layout = BoxLayout(orientation = "vertical")
        self.caller = caller
        
        self.filechooser = FileChooserListView()
        self.filechooser.bind(on_submit = self.select_file)
        self.layout.add_widget(self.filechooser)
        
        self.textinput = TextInput(size_hint_y = None, height = 30, multiline = False)
        self.layout.add_widget(self.textinput)
        
        self.savebar = BoxLayout(size_hint_y = None, height = 30)
        self.save_btn = Button(text = "Save", size_hint_y = None, height = 30)
        self.save_btn.bind(on_release = self.save_sheet)
        self.savebar.add_widget(self.save_btn)
        self.cancel_btn = Button(text = "Cancel", size_hint_y = None, height = 30)
        self.cancel_btn.bind(on_release = self.dismiss)
        self.savebar.add_widget(self.cancel_btn)
        self.layout.add_widget(self.savebar)
        
        self.content = self.layout
    def select_file(self, chooser, selection, touch):
        if len(chooser.selection) > 0:
            self.textinput.text = chooser.selection[0]
    def save_sheet(self, btn):
        try:
            filename = self.textinput.text
            linebreak = filename.rfind("\n") # if enter had been hit in text box
            if linebreak > -1:
                filename = filename[(linebreak+1):]
            mycon = open(os.path.join(self.filechooser.path, filename), mode = "wt")
            
            # write header
            mycon.write("#MetaChar version {}\n\n".format(version_str))
            
            # write each StatBar to the file
            mycon.write("<masterstatlist>\n\n")
            [s.write_to_file(mycon) for s in masterstatlist]
            mycon.write("</masterstatlist>\n\n")
            
            # write each BoxOfStats to the file
            mycon.write("<MCpages>\n\n")
            [p.write_to_file(mycon) for p in self.caller.parent.statspages]
            mycon.write("</MCpages>\n\n")
        finally:
            mycon.close()
            self.dismiss()
            
# popup for loading sheet
class LoadPopup(Popup):
    def __init__(self, caller, **kwargs):
        Popup.__init__(self, **kwargs)
        self.title = "Load character sheet"
        self.layout = BoxLayout(orientation = "vertical")
        self.caller = caller
        
        self.filechooser = FileChooserListView()
        self.filechooser.bind(on_submit = self.select_file)
        self.layout.add_widget(self.filechooser)
        
        self.textinput = TextInput(size_hint_y = None, height = 30, multiline = False)
        self.layout.add_widget(self.textinput)
        
        self.loadbar = BoxLayout(size_hint_y = None, height = 30)
        self.load_btn = Button(text = "Load", size_hint_y = None, height = 30)
        self.load_btn.bind(on_release = self.load_sheet)
        self.loadbar.add_widget(self.load_btn)
        self.cancel_btn = Button(text = "Cancel", size_hint_y = None, height = 30)
        self.cancel_btn.bind(on_release = self.dismiss)
        self.loadbar.add_widget(self.cancel_btn)
        self.layout.add_widget(self.loadbar)
        
        self.content = self.layout
        
    def select_file(self, chooser, selection, touch):
        if len(chooser.selection) > 0:
            self.textinput.text = chooser.selection[0]
    def load_sheet(self, btn):
        global masterstatlist
        try:
            filename = self.textinput.text
            linebreak = filename.rfind("\n") # if enter had been hit in text box
            if linebreak > -1:
                filename = filename[(linebreak+1):]
            mycon = open(os.path.join(self.filechooser.path, filename), mode = "rt")
            filetext = mycon.read()
            filestruct = read_xml(filetext)
            masterstatlist = [] # clear existing stat list
            # clear pages
            [self.caller.parent.remove_widget(sp) for sp in self.caller.parent.statspages] 
            self.caller.parent.statspages = []
            # read masterstatlist
            for s in filestruct[0][1]:
                thisclass = globals()[s[0]] # the class of statbar we are making
                initvals = dict() # to hold argument values for initialization
                attrvals = [] # to hold values for additional attributes
                for a in s[1]: # loop through attributes
                    if a[0] in initargs:
                        if a[0] not in {"statlist_existing", "stat_to_div"}:
                            # convert to right format and add to dict for initialization
                            initvals[a[0]] = conv_fns[a[0]](a[1])  
                    else:
                        if a[0] != "childstats.statlist":
                            # convert to right format and add to attribute list
                            attrvals.append([a[0], conv_fns[a[0]](a[1])])
                thissb = thisclass(**initvals) # the statbar object
                for a in attrvals:
                    # set additional attributes
                    if a[0] == 'statbtn.size_hint_x':
                        thissb.statbtn.size_hint_x = a[1]
                    else:
                        setattr(thissb, a[0], a[1])
                masterstatlist.append(thissb)  # add to masterstatlist
            # connect stats to each other
            for i in range(len(masterstatlist)):
                if isinstance(masterstatlist[i], StatBarSum):
                    se_text = [a[1] for a in filestruct[0][1][i][1] if a[0] == "statlist_existing"][0]
                    sn_text = [a[1] for a in filestruct[0][1][i][1] if a[0] == "childstats.statlist"][0]
                    se = conv_statlist(se_text) # existing stats
                    sn = conv_statlist(sn_text) # stats just within this stat
                    masterstatlist[i].statlist_existing = se
                    masterstatlist[i].childstats.statlist = sn
                    masterstatlist[i].childstats.redraw() # calls add widget to add to BoxOfStats
                    masterstatlist[i].update_button_text()
                if isinstance(masterstatlist[i], StatBarFraction):
                    sd_text = [a[1] for a in filestruct[0][1][i][1] if a[0] == "stat_to_div"][0]
                    sd = conv_stat(sd_text)
                    masterstatlist[i].stat_to_div = sd
                    masterstatlist[i].update_button_text()
            # read MCpages (list of box of stats)
            for b in filestruct[1][1]:
                attrvals = [] # color attributes to add
                for x in b[1]:
                    if x[0] == 'statlist':
                        thisstatlist = conv_fns[x[0]](x[1])
                    else:
                        attrvals.append([x[0], conv_fns[x[0]](x[1])])
                thisbox = BoxOfStats(statlist = thisstatlist)
                for a in attrvals:
                    setattr(thisbox, a[0], a[1])
                self.caller.parent.statspages.append(thisbox)
                self.caller.parent.add_widget(thisbox)
            # update text colors now that we have background colors
            [st.update_text_color() for st in masterstatlist]
            # leave edit mode for all pages
            [sb.leave_edit_mode(None) for sb in self.caller.parent.statspages]
        finally:
            mycon.close()
            self.dismiss()
        
# A front page with buttons for adding pages, saving, etc.
class FrontPage(BoxLayout):
    def __init__(self, **kwargs):
        BoxLayout.__init__(self, **kwargs)
        self.orientation = "vertical"
        self.spacing = 3
        self.padding = 3
        
        self.add_widget(Label(text = "MetaChar v. {}\nCustom character sheets!".format(version_str)))
        
        self.save_btn = Button(text = "Save character sheet")
        self.save_btn.bind(on_release = self.open_save_dialog)
        self.add_widget(self.save_btn)
        
        self.load_btn = Button(text = "Load character sheet")
        self.load_btn.bind(on_release = self.open_load_dialog)
        self.add_widget(self.load_btn)
        
        self.add_pg_btn = Button(text = "Add new page")
        self.add_pg_btn.bind(on_release = self.add_page)
        self.add_widget(self.add_pg_btn)
        
        self.dd5e_btn = Button(text = "New character from D&D 5e template")
        self.dd5e_btn.bind(on_release = self.dd5e_template)
        self.add_widget(self.dd5e_btn)
        
        self.clear_btn = Button(text = "Clear all pages")
        self.add_widget(self.clear_btn)
        self.clear_btn.bind(on_release = self.clear_pages)
    def open_save_dialog(self, btn):
        self._popup = SavePopup(caller = self)
        self._popup.open()
    def open_load_dialog(self, btn):
        self._popup = LoadPopup(caller = self)
        self._popup.open()
    def add_page(self, btn):
        newpg = BoxOfStats(statlist = [])
        self.parent.statspages.append(newpg)
        self.parent.add_widget(newpg)
    def dd5e_template(self, btn):
        global masterstatlist
        masterstatlist = []
        [self.parent.remove_widget(sp) for sp in self.parent.statspages]
        self.parent.statspages = make_5e_template()
        [self.parent.add_widget(sp) for sp in self.parent.statspages]
    def clear_pages(self, btn):
        global masterstatlist
        masterstatlist = []
        [self.parent.remove_widget(sp) for sp in self.parent.statspages]
        self.parent.statspages = []
        newpg = BoxOfStats(statlist = [])
        self.parent.statspages.append(newpg)
        self.parent.add_widget(newpg)
        
# The layout for pages with character sheet info
# Currently set up as dummy for testing
class MCpages(PageLayout):
    def __init__(self, **kwargs):
        PageLayout.__init__(self, **kwargs)
        # main page for adding pages, saving, etc.
        self.frntpg = FrontPage()
        self.add_widget(self.frntpg)
        # list to contain all stats pages (BoxOfStats)
        self.statspages = []
        
        # dummy stats for this example
        self.statlist = [#DDAbilityBar(statname = "STR", statdesc = "Strength", statval = 13),
                    #DDAbilityBar(statname = "DEX", statdesc = "Dexterity", statval = 10),
                    StatBarSimple(statname = "Prof. bonus", statdesc = "Proficiency bonus", statval = 2,
                                  showplus = True, calcavail = True)]
        self.statlist.append(StatBarSum(statname = "Athletics", statdesc = "stuff", showplus = True,
                                statlist_existing = [self.statlist[0]],#, self.statlist[2]],
                                statlist_new = []))
        self.statlist.append(StatBarCounter(statname = "Hit Points", statdesc = "You know", defaultval = 8, calcavail = True))
        self.statlist.append(StatBarFraction(statname = "hp/2", statdesc = "", stat_to_div = self.statlist[2],
                                             divisor = 2, rounddown = False))
        masterstatlist.extend(self.statlist) # put them in master list too
        self.statspages.append(BoxOfStats(statlist = self.statlist))
        
        # add all stats pages
        [self.add_widget(sp) for sp in self.statspages]


# The screen with pages with character sheet info        
#class MCscreen(Screen):
#    def __init__(self, **kwargs):
#        Screen.__init__(self, **kwargs)
#        self.add_widget(MCpages())

# class for the app as a whole        
class MetaChar(App):
    def build(self):
        self.mc = MCpages()
        Window.bind(on_key_down = self.key_action)
        return self.mc
    def on_pause(self):
        return True
    def key_action(self, *args):
        keynum = args[1]
        # swipe left with left arrow
        if keynum == 276 and self.mc.page > 0 and not edit_window_open: 
            self.mc.page -= 1
        # swipe right with right arrow
        if keynum == 275 and self.mc.page < (len(self.mc.children) - 1) and not edit_window_open: 
            self.mc.page += 1

# template for a D&D 5e character
def make_5e_template():
    global masterstatlist
    
    # Page with basic biographical information
    plyr_name = StatBarText(statname = "Name", statdesc = "Name of the character",
                            stattext = "Sample Exampleson")
    plyr_race = StatBarText(statname = "Race", statdesc = "Human, elf, dwarf, halfling, etc., including subraces.",
                            stattext = "Human")
    plyr_level = StatBarSimple(statname = "Level", statdesc = "Overall level for your character", statval = 1)
    plyr_class = StatBarText(statname = "Class", statdesc = "Like, are you a figher or a wizard or a bard or what?",
                             stattext = "Toilet mage")
    plyr_spec = StatBarText(statname = "Specialization", statdesc = "Most classes have two or more options to choose from at an early level.", stattext = "")
    plyr_bkgd = StatBarText(statname = "Background", statdesc = "Who you were before you were an adventurer, or what you do now when you aren't adventuring.  Comes with a couple skill proficiencies and other perks.", stattext = "Sailor")
    plyr_lng = StatBarText(statname = "Languages known", statdesc = "Various races have their own languages that they speak.  Your character might know some of them depending on race, class, and background.", stattext = "Common")
    plyr_bio = StatBar(statname = "Biography", statdesc = "Fill in any extra info here.  You may also wish to add boxes for alignment, ideals, bonds, and flaws.")
    plyr_bio.statbtn.size_hint_x = 1
    bio_page = BoxOfStats(statlist = [plyr_name, plyr_race, plyr_level, plyr_class, plyr_spec, plyr_bkgd, plyr_lng, plyr_bio])
    # color scheme from the "viridis" R package
    bio_page.red_bg = 0.992
    bio_page.green_bg = 0.906
    bio_page.blue_bg = 0.145
    masterstatlist.extend(bio_page.statlist)

    # Page with ability scores and proficiency bonus
    ability_header = StatBar(statname = "Ability Scores and Proficiency Bonus",
                             statdesc = "These scores are rarely used by themselves, but are used for calculating other roll modifiers.  Ability scores indicate things like how smart or strong your character is overall, and your proficiency bonus indicates just how good they are at their particular skills.\n\nAfter an ability score, an automatically-calculated roll modifier is listed in parentheses.  Ability scores are the sum of a number you choose at character creation, any racial modifiers, and any increases gained at certain levels.\n\nThe proficiency bonus is dependent only on character level.")
    ability_header.statbtn.size_hint_x = 1
    ability_desc = "{0}.  To make a {1} check, roll 1d20 and add the number in parentheses."
    base_stat_desc = "Number you selected at level 1."
    hum_mod_desc = "Human racial modifier to {}."
    STR = DDAbilityBar(statname = "STR", 
                       statdesc = ability_desc.format("Strength", "strength"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base STR", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("strength"), statval = 1,
                                                     showplus = True)])
    DEX = DDAbilityBar(statname = "DEX", 
                       statdesc = ability_desc.format("Dexterity", "dexterity"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base DEX", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("dexterity"), statval = 1,
                                                     showplus = True)])
    CON = DDAbilityBar(statname = "CON", 
                       statdesc = ability_desc.format("Constitution", "constitution"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base CON", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("constitution"), statval = 1,
                                                     showplus = True)])
    INT = DDAbilityBar(statname = "INT", 
                       statdesc = ability_desc.format("Intelligence", "intelligence"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base INT", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("intelligence"), statval = 1,
                                                     showplus = True)])
    WIS = DDAbilityBar(statname = "WIS", 
                       statdesc = ability_desc.format("Wisdom", "wisdom"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base WIS", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("wisdom"), statval = 1,
                                                     showplus = True)])
    CHA = DDAbilityBar(statname = "CHA", 
                       statdesc = ability_desc.format("Charisma", "charisma"),
                       statlist_existing = [],                     
                       statlist_new = [StatBarSimple(statname = "Level 1 base CHA", 
                                                     statdesc = base_stat_desc, statval = 10),
                                       StatBarSimple(statname = "Human",
                                                     statdesc = hum_mod_desc.format("charisma"), statval = 1,
                                                     showplus = True)])
    prof = StatBarSimple(statname = "Proficiency bonus",
                         statdesc = "Added to d20 rolls where you are proficient in a skill, weapon, or save.  Increases at certain levels.", statval = 2, showplus = True, calcavail = True)
    ability_page = BoxOfStats(statlist = [ability_header, STR, DEX, CON, INT, WIS, CHA, prof])
    ability_page.red_bg = 0.624
    ability_page.green_bg = 0.855
    ability_page.blue_bg = 0.227
    masterstatlist.extend(ability_page.statlist)
    
    # Page with saving throws
    saving_throw_header = StatBar(statname = "Saving throws",
                                  statdesc = "These are rolls you make to keep something bad from happening to you.  The DM will tell you if you need to make a saving throw.  Roll 1d20 and add the indicated modifier.\n\nWhen you make your character sheet, edit the appropriate saving throws, adding your proficiency bonus using \"Add existing stat\".")
    saving_throw_header.statbtn.size_hint_x = 1
    str_save = StatBarSum(statname = "STR save", statdesc = "Roll modifier for strength saving throw.",
                          statlist_existing = [STR], statlist_new = [], showplus = True)
    dex_save = StatBarSum(statname = "DEX save", statdesc = "Roll modifier for dexterity saving throw.",
                          statlist_existing = [DEX], statlist_new = [], showplus = True)
    con_save = StatBarSum(statname = "CON save", statdesc = "Roll modifier for constitution saving throw.",
                          statlist_existing = [CON], statlist_new = [], showplus = True)
    int_save = StatBarSum(statname = "INT save", statdesc = "Roll modifier for intelligence saving throw.",
                          statlist_existing = [INT], statlist_new = [], showplus = True)
    wis_save = StatBarSum(statname = "WIS save", statdesc = "Roll modifier for wisdom saving throw.",
                          statlist_existing = [WIS], statlist_new = [], showplus = True)
    cha_save = StatBarSum(statname = "CHA save", statdesc = "Roll modifier for charisma saving throw.",
                          statlist_existing = [CHA], statlist_new = [], showplus = True)
    death_success = StatBarCounter(statname = "Death save successes", 
                                   statdesc = "If you are dying, roll a d20 at the beginning of your turn.  10 or higher counts as a success.  If you get three successes, you are no longer dying.",
                                   defaultval = 0)
    death_fail = StatBarCounter(statname = "Death save failures",
                                statdesc = "If you are dying, roll a d20 at the beginning of your turn.  9 or lower counts as a failure (1 as two failures).  If you get three failures, you are dead.",
                                defaultval = 0)
    saving_throw_page = BoxOfStats(statlist = [saving_throw_header, str_save, dex_save, con_save, int_save,
                                               wis_save, cha_save, death_success, death_fail])
    saving_throw_page.red_bg = 0.29
    saving_throw_page.green_bg = 0.757
    saving_throw_page.blue_bg = 0.427
    masterstatlist.extend(saving_throw_page.statlist)
    
    # page with hit points, armor class, and attack modifiers
    hit_point_max = StatBarSum(statname = "Max. hit points",
                               statdesc = "This value increases with each level according to class.  Add your CON bonus with \"Add existing stat\"; HP increases retroactively with CON increase.",
                               statlist_existing = [CON], 
                               statlist_new = [StatBarSimple(statname = "Level 1 base hp",
                                                             statdesc = "Base hit points at level 1 for wizard.",
                                                             statval = 6)])
    hit_point_current = StatBarCounter(statname = "Current hit points",
                                       statdesc = "If this gets down to zero, you are dying.",
                                       defaultval = 6)
    hit_dice = StatBarText(statname = "Hit dice",
                           statdesc = "These are the dice you use to regain hit points when you rest.  Your class determines this.",
                           stattext = "1d6")
    armor_class = StatBarSum(statname = "Armor class",
                             statdesc = "The higher it is, the harder you are to hit.  Check the type of armor you are wearing to see if your dexterity bonus should be added.",
                             statlist_existing = [DEX], 
                             statlist_new = [StatBarSimple(statname = "Padded", statdesc = "Armor class of padded armor.",
                                                           statval = 11)])
    initiative = StatBarSum(statname = "Initiative",
                            statdesc = "Determines combat order.  Generally just your dexterity modifier.\n\nRoll 1d20 and add the modifier.",
                            statlist_existing = [DEX], statlist_new = [], showplus = True)
    melee_atk = StatBarSum(statname = "Melee attack mod.",
                           statdesc = "When attacking with a melee weapon, add this modifier to a 1d20 roll to determine if you hit.  Also use this modifier for attacks with a finesse weapon if your strength is better than your dexterity.  Remove the proficiency bonus if using a weapon in which you are not proficient.",
                           statlist_existing = [STR, prof], statlist_new = [], showplus = True)
    melee_dmg = StatBarSum(statname = "Melee damage mod.",
                           statdesc = "When attacking with a melee weapon, add this modifier to the damage dice for the weapon.  Also use this modifier for damage from a finesse weapon if your strength is better than your dexterity.",
                           statlist_existing = [STR], statlist_new = [], showplus = True)
    ranged_atk = StatBarSum(statname = "Ranged attack mod.",
                           statdesc = "When attacking with a ranged weapon, add this modifier to a 1d20 roll to determine if you hit.  Also use this modifier for attacks with a finesse weapon if your dexterity is better than your strength.  Remove the proficiency bonus if using a weapon in which you are not proficient.",
                           statlist_existing = [DEX, prof], statlist_new = [], showplus = True)
    ranged_dmg = StatBarSum(statname = "Ranged damage mod.",
                           statdesc = "When attacking with a melee weapon, add this modifier to the damage dice for the weapon.  Also use this modifier for damage from a finesse weapon if your dexterity is better than your strength.",
                           statlist_existing = [DEX], statlist_new = [], showplus = True)
    combat_page = BoxOfStats(statlist = [hit_point_max, hit_point_current, hit_dice, armor_class, initiative,
                                         melee_atk, melee_dmg, ranged_atk, ranged_dmg])
    combat_page.red_bg = 0.122
    combat_page.green_bg = 0.631
    combat_page.blue_bg = 0.529
    masterstatlist.extend(combat_page.statlist)
    
    # skills page 1
    skill_desc = "Roll 1d20 and add this modifier to make a{} {} check."
    skillpg_desc = "Skills pertain to various activities you might attempt out of combat.  Roll 1d20 and add the appropriate modifier to make a skill check.\n\nWhen making your character sheet, be sure to add your proficiency bonus to any skills in which you are proficient, using \"Add existing stat\".  Your class and background determine skill proficiencies."
    skills_header1 = StatBar(statname = "Skills page 1", statdesc = skillpg_desc)
    skills_header1.statbtn.size_hint_x = 1
    acrobatics = StatBarSum(statname = "Acrobatics", statdesc = skill_desc.format("n", "acrobatics"),
                            statlist_existing = [DEX], statlist_new = [], showplus = True)
    animal_handling = StatBarSum(statname = "Animal handling", statdesc = skill_desc.format("n", "animal handling"),
                            statlist_existing = [WIS], statlist_new = [], showplus = True)
    arcana = StatBarSum(statname = "Arcana", statdesc = skill_desc.format("n", "arcana"),
                            statlist_existing = [INT], statlist_new = [], showplus = True)
    athletics = StatBarSum(statname = "Athletics", statdesc = skill_desc.format("n", "athletics"),
                            statlist_existing = [STR], statlist_new = [], showplus = True)
    deception = StatBarSum(statname = "Deception", statdesc = skill_desc.format("", "deception"),
                            statlist_existing = [CHA], statlist_new = [], showplus = True)
    history = StatBarSum(statname = "History", statdesc = skill_desc.format("", "history"),
                            statlist_existing = [INT], statlist_new = [], showplus = True)
    insight = StatBarSum(statname = "Insight", statdesc = skill_desc.format("n", "insight"),
                            statlist_existing = [WIS], statlist_new = [], showplus = True)
    intimidation = StatBarSum(statname = "Intimidation", statdesc = skill_desc.format("n", "intimidation"),
                            statlist_existing = [CHA], statlist_new = [], showplus = True)
    investigation = StatBarSum(statname = "Investigation", statdesc = skill_desc.format("n", "investigation"),
                            statlist_existing = [INT], statlist_new = [], showplus = True)
    skills_page1 = BoxOfStats(statlist = [skills_header1, acrobatics, animal_handling, arcana, athletics,
                                          deception, history, insight, intimidation, investigation])
    skills_page1.red_bg = 0.153
    skills_page1.green_bg = 0.498
    skills_page1.blue_bg = 0.557
    masterstatlist.extend(skills_page1.statlist)
    
    # skills page 2
    skills_header2 = StatBar(statname = "Skills page 2", statdesc = skillpg_desc)
    skills_header2.statbtn.size_hint_x = 1
    medicine = StatBarSum(statname = "Medicine", statdesc = skill_desc.format("", "medicine"),
                            statlist_existing = [WIS], statlist_new = [], showplus = True)
    nature = StatBarSum(statname = "Nature", statdesc = skill_desc.format("", "nature"),
                            statlist_existing = [INT], statlist_new = [], showplus = True)
    perception = StatBarSum(statname = "Perception", statdesc = skill_desc.format("", "perception"),
                            statlist_existing = [WIS], statlist_new = [], showplus = True)
    performance = StatBarSum(statname = "Performance", statdesc = skill_desc.format("", "performance"),
                            statlist_existing = [CHA], statlist_new = [], showplus = True)
    persuasion = StatBarSum(statname = "Persuasion", statdesc = skill_desc.format("", "persuasion"),
                            statlist_existing = [CHA], statlist_new = [], showplus = True)
    religion = StatBarSum(statname = "Religion", statdesc = skill_desc.format("", "religion"),
                            statlist_existing = [INT], statlist_new = [], showplus = True)
    sleight_of_hand = StatBarSum(statname = "Sleight of Hand", statdesc = skill_desc.format("", "sleight of hand"),
                            statlist_existing = [DEX], statlist_new = [], showplus = True)
    stealth = StatBarSum(statname = "Stealth", statdesc = skill_desc.format("", "stealth"),
                            statlist_existing = [DEX], statlist_new = [], showplus = True)
    survival = StatBarSum(statname = "Survival", statdesc = skill_desc.format("", "survival"),
                            statlist_existing = [WIS], statlist_new = [], showplus = True)
    skills_page2 = BoxOfStats(statlist = [skills_header2, medicine, nature, perception, performance,
                                          persuasion, religion, sleight_of_hand, stealth, survival])
    skills_page2.red_bg = 0.212
    skills_page2.green_bg = 0.361
    skills_page2.blue_bg = 0.553
    masterstatlist.extend(skills_page2.statlist)
    
    # spells page 1
    spells_header = StatBar(statname = "Spells",
                            statdesc = "This page contains stats pertaining to spells, as well as examples of how you can store spell descriptions in rows of buttons.")
    spells_header.statbtn.size_hint_x = 1
    spell_atk = StatBarSum(statname = "Spell attack mod.",
                           statdesc = "When using a spell where you roll to hit, add this modifier to a 1d20 roll to determine if you hit.  This will use either your INT, WIS, or CHA modifier depending on class.",
                           statlist_existing = [CHA, prof], statlist_new = [], showplus = True)
    spell_save = StatBarSum(statname = "Spell save DC",
                            statdesc = "If a target of one of your spells must make a saving throw to avoid negative effects from the spell, this is the number they are trying to beat.  It is calculated with INT, WIS, or CHA depending on your class.",
                            statlist_existing = [CHA, prof], 
                            statlist_new = [StatBarSimple(statname = "Base spell save DC", 
                                                          statdesc = "This is always 8.", statval = 8)])
    spell_slots1 = StatBarCounter(statname = "Level 1 spell slots",
                                  statdesc = "This is how many level 1 spells you can cast before you need a rest.",
                                  defaultval = 3)
    spell_slots2 = StatBarCounter(statname = "Level 2 spell slots",
                                  statdesc = "This is how many level 2 spells you can cast before you need a rest.",
                                  defaultval = 1)
    example_cantrip = StatBarText(statname = "Plunger ray", 
                                  statdesc = "Here you would put a more detailed description of this spell.",
                                  stattext = "2d6 damage")
    example_spells = StatBarThreeButtons(statname = "Some spell", statdesc = "Spell description",
                                         statname2 = "Another spell", statdesc2 = "Spell description",
                                         statname3 = "A third spell", statdesc3 = "Spell description")
    spell_page = BoxOfStats(statlist = [spells_header, spell_atk, spell_save, spell_slots1, spell_slots2,
                                        example_cantrip, example_spells])
    spell_page.red_bg = 0.275
    spell_page.green_bg = 0.2
    spell_page.blue_bg = 0.494
    masterstatlist.extend(spell_page.statlist)
    
    # additional traits
    additional_header = StatBar(statname = "Additional traits",
                                statdesc = "Anything else not already covered.")
    additional_header.statbtn.size_hint_x = 1
    example_stuff = StatBarText(statname = "Being awesome", statdesc = "blah blah blah",
                                stattext = "General awesomeness")
    additional_page = BoxOfStats(statlist = [additional_header, example_stuff])
    additional_page.red_bg = 0.267
    additional_page.green_bg = 0.004
    additional_page.blue_bg = 0.329
    masterstatlist.extend(additional_page.statlist)
    
    [st.update_text_color() for st in masterstatlist]
    
    return [bio_page, ability_page, saving_throw_page, combat_page, skills_page1, skills_page2, spell_page, 
            additional_page]
            
# Run the program
if __name__ == '__main__':
    MetaChar().run()