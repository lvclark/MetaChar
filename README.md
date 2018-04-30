# MetaChar

This is a graphical program for creating, editing, viewing, and interacting with
customizable character sheets for tabletop gaming.  It comes with a template for
Dungeons & Dragons 5e characters, but has the flexibility to handle all sorts of
homebrew, or different systems entirely.  It is made using Python 3 and Kivy.

This is a platform-independent program, designed to run on a tablet or small 
laptop.  Your character sheet consists of a number of pages that you can flip
through by swiping or using the arrow keys.  For every item on your sheet, there
is a button where you can add a popup with a lengthy description, which is handy
for spells or for rules that you haven't memorized.  You also have the ability 
to track how each stat was calculated.  Stats can be calculated as fractions or
sums of other stats, and/or from numbers that only pertain to that particular sum.

## Installing

If coding is your thing, you can run MetaChar from the source using Python 3.6 and
Kivy 1.10.

For Windows users who don't want to bother installing Python/Kivy, download the
zip file of the Windows binary from the latest release on the 
[releases](https://github.com/lvclark/MetaChar/releases) page.
Unzip it.  Make a desktop shortcut to the file "metachar.exe".  Double-click that
shortcut to launch the program.

On Android, you'll need an app called Kivy Launcher.  On your SD card, in a folder
called Kivy, add a new folder called MetaChar, and then add the files from this 
repository ("main.py", "metachar.kv", and "android.txt") to that folder.  Now you
should be able to access MetaChar from Kivy Launcher.

## License

This software is released under the GNU General Public Licence v3.  In summary, you
may use, modify, and distribute this software however you like, as long as it is 
distributed under the same license.  This software comes with no warranty.
