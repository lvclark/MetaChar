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
If you update the value of a stat, for example when leveling up your character,
all stats derived from it are automatically updated.

## Installing

If coding is your thing, you can run MetaChar from the source using Python 3.6 and
Kivy 1.10.  `main.py` and `metachar.kv` are the only files that you need in order
to run the program from the source.

For Windows users who don't want to bother installing Python/Kivy, download the
zip file of the Windows binary from the latest release on the 
[releases](https://github.com/lvclark/MetaChar/releases) page.
Unzip it.  Make a desktop shortcut to the file "metachar.exe".  Double-click that
shortcut to launch the program.

Hypothetically it should work on Android with the Kivy Launcher app, but currently
it simply crashes the app.

## License

This software is released under the GNU General Public License v3.  In summary, you
may use, modify, and distribute this software however you like, as long as it is 
distributed under the same license.  This software comes with no warranty.
