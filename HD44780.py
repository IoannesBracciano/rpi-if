# Copyright (c) 2017 Ioannes Bracciano
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# TODO Implement reading data back from the controller through the rw pin
#      Currently not implemented as voltage incompatibility between the HD44780
#      and the RPi require a regulator so as not to burn the latter
#
# Author and Maintainer
# Ioannes Bracciano <john.bracciano@gmail.com>


"""
  This module Provides an interface for HD44780 controllers, or other
  controllers that have a similar instruction set as HD44780
"""


from RPi import GPIO as GPIO
from time import sleep


###########################
# --- INSTRUCTION SET --- #
###########################

                        #                Pin order              #
                        # RS RW DB7 DB6 DB5 DB4 DB3 DB2 DB1 DB0 #

# Clear Display (wipes out DDRAM contents)
__INSTR_CLR_DISP                      = 0b0000000001

# Return Home (DDRAM contents do not change)
__INSTR_RET_HOME                      = 0b0000000010

# Set entry mode (shift direction and cursor or screen shift)
__INSTR_ENTRY_MODE_SET                = 0b0000000100

# Control display and cursor appearance
__INSTR_DISP_ON_OFF_CTRL              = 0b0000001000

# Shift cursor or screen
__INSTR_SHIFT                         = 0b0000010000

# Set function of controller
__INSTR_FUNCTION_SET                  = 0b0000100000

# Sets the CGRAM address. CGRAM is where user can load
# up to 8 of his own dot patterns for display on the sreen
# Remember to replace last 6 bits with the actual address
__INSTR_SET_CGRAM_ADDR                = 0b0001000000

# Sets the DDRAM address
# In single line display mode, the addresses span from
# 0x00 to 0x4f
# When both lines of text are used, the addresses span
# from 0x00 to 0x27 for th first line and from 0x40 to
# 0x67 for the second line
# Remember to replace last 7 bits with the actual address
__INSTR_SET_DDRAM_ADDR                = 0b0010000000

# Writes data to CGRAM or DDRAM, according to the
# previously set address (see __INSTR_SET_xxRAM_ADDR)
# Remember to replace last 8 bits with the character code
__INSTR_WRITE                         = 0b1000000000


# Flags for __INSTR_MODE_ENTRY_SET
__FLAG_CURSOR_DECR                    = 0b00
__FLAG_CURSOR_INCR                    = 0b10

# Flags for __INSTR_DISP_ON_OFF_CTRL
__FLAG_DISP_OFF                       = 0b000
__FLAG_DISP_ON                        = 0b100

# Flags for __INSTR_SHIFT
__FLAG_SHIFT_CURSOR                   = 0b0000
__FLAG_SHIFT_SCREEN                   = 0b1000
__FLAG_DIR_LEFT                       = 0b0000
__FLAG_DIR_RIGHT                      = 0b0100

# Flags for __INSTR_FUNCTION_SET
__FLAG_4_BITS                         = 0b00000
__FLAG_8_BITS                         = 0b10000
__FLAG_1_LINE                         = 0b00000
__FLAG_2_LINES                        = 0b01000
__FLAG_5X8_FONT                       = 0b00000
__FLAG_5X10_FONT                      = 0b00100


# Various default values
# Default pin numbers (BCM numbering)
PIN_DEFS = {
    'rs':    21 if GPIO.RPI_REVISION==1 else 27,
    'e' :    22,
    'db':   [4, 25, 24, 23] }
#            ^  ^   ^   ^
#          DB7 DB6 DB5 DB4
__DEFAULT_NUM_LINES = 1
__DEFAULT_FONT = "5x8"


from sys import modules

# Getting a pointer to this module
this = modules[__name__]


# Initializes HD44780 driver
# This needs to be called before any other function, providing the correct
# pin numbers (BCM numbering, most significant first)
def init (pins=None):
  """ Initialize the module and the controller
  """
  if pins:
    if "rs" not in pins or "e" not in pins or "db" not in pins:
      raise KeyError("Invalid format of pins dictionary.\
          Keys 'rs', 'e' and 'db' must be included")

  this.__pins = pins or PIN_DEFS

  GPIO.setmode(GPIO.BCM)
  GPIO.setup(this.__pins['rs'], GPIO.OUT)
  GPIO.output(this.__pins['rs'], GPIO.LOW)
  GPIO.setup(this.__pins['e'], GPIO.OUT)
  GPIO.output(this.__pins['e'], GPIO.LOW)
  for i in range(len(this.__pins['db'])):
    GPIO.setup(this.__pins['db'][i], GPIO.OUT)
    GPIO.output(this.__pins['db'][i], GPIO.LOW)

  this.__bit_mode = len(this.__pins['db'])

  # Initialization process requires to send the 'Set Function'
  # instruction 3 times at specific time intervals
  # For more info checkout
  # http://www.8051projects.net/lcd-interfacing/initialization.php
  GPIO.output(this.__pins['db'][2], GPIO.HIGH)
  GPIO.output(this.__pins['db'][3], GPIO.HIGH)
  __signal_enable()
  sleep(0.005)
  __signal_enable()
  sleep(0.001)
  __signal_enable()

  if this.__bit_mode == 4:
    GPIO.output(this.__pins['db'][3], GPIO.LOW)
    __signal_enable()
    sleep(0.001)

  set_function(   bit_mode = len(this.__pins['db']),
                  num_lines = this.__DEFAULT_NUM_LINES,
                  font = this.__DEFAULT_FONT   )

  # Initialization process complete
  # Clear the screen
  clear()


def clear():
  """ Clear the display
  """
  __instruct(this.__INSTR_CLR_DISP)


def home():
  """ Shift to original position and return cursor to the beginning of the
  screen
  """
  __instruct(this.__INSTR_RET_HOME)


def set_entry_mode(mode="incr", shift_screen=False):
  """ Set whether cursor position will increment or decrement after each
  `write` instruction, and whether the screen will shift with  the cursor
  
  Parameters
  ----------
  mode : {'incr', 'decr'}, optional
       whether the cursor position will increment or decrement
  shift_screen : {False, True}, optional
       whether the screen will shift with the cursor

  Raises
  ------
  ValueError
       if any of `mode` or `shift_screen` arguments have an invalid value
  """
  if mode not in ("incr", "decr"):
    raise ValueError("`mode` should be either 'incr' or 'decr', was: {}"\
        .format(mode))
  if shift_screen not in (False, True):
    raise ValueError("`shift_screen` should be either True or False, was: {}"\
        .format(shift_screen))

  if mode == "decr":
    __instruct(   this.__INSTR_ENTRY_MODE_SET
                | this.__FLAG_CURSOR_DECR
                | shift_screen   )
  elif mode == "incr":
    __instruct(   this.__INSTR_ENTRY_MODE_SET
                | this.__FLAG_CURSOR_INCR
                | shift_screen   )


def display_on(cursor=False, blink=False):
  """ Turn display on and configure cursor appearance

  Parameters
  ----------
  cursor : {False, True}, optional
       controls the cursor visibility.
       Set to False (default) to hide the cursor, True to show it
  blink : {False, True}, optional
       controls the cursor blink.
       Set to False (default) to show static cursor, True to blink
  
  Raises
  ------
  ValueError
       if any of the `cursor`, `blink` arguments have an invalid value
  """
  if cursor not in (False, True):
    raise ValueError("`cursor` should be either True or False, was: {}"\
        .format(shift_screen))
  if blink not in (False, True):
    raise ValueError("`blink` should be either True or False, was: {}"\
        .format(shift_screen))

  __instruct(   this.__INSTR_DISP_ON_OFF_CTRL
              | this.__FLAG_DISP_ON
              | (cursor << 1)
              | blink   )


def display_off():
  """ Turn display off
  """
  __instruct(this.__INSTR_DISP_ON_OFF_CTRL | this.__FLAG_DISP_OFF)


def move_cursor(direction):
  """ Move the cursor one position to the specified direction

  Parameters
  ----------
  direction : {'right', 'left'}
       the direction of cursor move
  """
  if direction == "left":
    __instruct(   this.__INSTR_SHIFT
                | this.__FLAG_SHIFT_CURSOR
                | this.__FLAG_DIR_LEFT   )
  elif direction == "right":
    __instruct(   this.__INSTR_SHIFT
                | this.__FLAG_SHIFT_CURSOR
                | this.__FLAG_DIR_RIGHT   )


def shift_display(direction):
  """ Shift the display by one position to the specified direction

  Parameters
  ----------
  direction : {'right', 'left'}
       the direction of display shift
  """
  if direction == "left":
    __instruct(   this.__INSTR_SHIFT
                | this.__FLAG_SHIFT_SCREEN
                | this.__FLAG_DIR_LEFT   )
  elif direction == "right":
    __instruct(   this.__INSTR_SHIFT
                | this.__FLAG_SHIFT_SCREEN
                | this.__FLAG_DIR_RIGHT   )


def set_function(bit_mode=4, num_lines=1, font="5x8"):
  """ Set various parameters of the controller

  Parameters
  ----------
  bit_mode : {4, 8}, optional
       the mode in which the controller must be interfaced. Corresponds to the
       number of data pins connected
  num_lines : {1, 2}, optional
       the number of lines available on the display
  font : {"5x8", "5x10"}
       which character font should be used

  Raises
  ------
  ValueError
       if any of `bit_mode`, `num_lines` or `font` arguments have an invalid
       value
  """
  if bit_mode not in (4,8):
    raise ValueError("Invalid bit mode set: {}".format(bit_mode))
  if num_lines not in (1,2):
    raise ValueError("Invalid number of lines set: {}".format(lines))
  if font not in ("5x8", "5x10"):
    raise ValueError("Invalid font: {}".format(font))
  
  # Keep number of lines and bit mode as they are needed for other functions
  this.__bit_mode = bit_mode
  this.__num_lines = num_lines

  __instruct(   this.__INSTR_FUNCTION_SET
              | (this.__FLAG_4_BITS if bit_mode == 4 else this.__FLAG_8_BITS)
              | (this.__FLAG_1_LINE if num_lines == 1 else this.__FLAG_2_LINES)
              | (this.__FLAG_5X8_FONT if font == "5x8" else this.__FLAG_5X10_FONT)
            )


def set_cgram_address(address):
  """ Specifies the address in CGRAM which subsequent instructions may
  write to or read from

  Parameters
  ----------
  address : int
       the address in CGRAM.
       Addresses in CGRAM span from 0x00 to 0x03 or 0x07, depending on the
       font that is used

  Raises
  ------
  ValueError
       if given `address` is outside of CGRAM address space
  """
  if address < 0x00 or address >0x3f:
    raise ValueError("Invalid CGRAM address set: {}\
        CGRAM address space spans from 0x00 to 0x3f".format(address))
  __instruct(this.__INSTR_SET_CGRAM_ADDR | (address & 0x3f))
                                            # avoid address overflowing to
                                            # other bits


def set_ddram_address(address):
  """ Specifies the address in CGRAM which subsequent instructions may
  write to or read from

  Parameters
  ----------
  address : int
       the address in DDRAM.
       Addresses in DDRAM span from 0x00 to 0x4f if using only 1 line,
       or from 0x00 to 0x27 for the first line and from 0x40 to 0x47 for
       the second one, if using 2 lines

  Raises
  ------
  ValueError
       if given `address` is outside of DDRAM address space
  """
  if this.__num_lines == 1:
    if address < 0x00 or address > 0x4f:
      raise ValueError("Invalid DDRAM address set: {}\
          DDRAM address space spans from 0x00 to 0x4f (1 line)".format(address))
     
  else:
    if address < 0x00 or address > 0x27 and address <0x40 or address > 0x67:
      raise ValueError("Invalid DDRAM address set: {}\
          DDRAM address space spans from 0x00 to 0x27 (first line) and\
          from 0x40 to 0x67 (second line)".format(address))

  __instruct(this.__INSTR_SET_DDRAM_ADDR | (address & 0x7f))
                                            # avoid address overflowing to
                                            # other bits


def write(stuff):
  """ Write `stuff` to DDRAM or CGRAM

  Parameters
  ----------
  stuff : array_like, str, int
       content to be written in DDRAM or CGRAM
  """
  if isinstance(stuff, list):
    for byte in stuff:
      __instruct(this.__INSTR_WRITE | (byte & 0xff))
  elif isinstance(stuff, str):
    for char in stuff:
      __instruct(this.__INSTR_WRITE | ord(char))
  elif isinstance(stuff, int):
    __instruct(this.__INSTR_WRITE | (stuff & 0xff))


# Signals the enable pin
# (sets it to HIGH and then back to LOW)
# When signaled, the 'enable' pin lets the
# currently formed instruction be executed.
# See the controller's documentation for the
# instruction codes
def __signal_enable():
  GPIO.output(this.__pins['e'], GPIO.HIGH)
  GPIO.output(this.__pins['e'], GPIO.LOW)


# Prepares the instruction and sends it to the controller
# depending on the bit mode selected
def __instruct(instruction):
  # Prepare bits
  bits = bin(instruction)[2:].zfill(10)
  # Prepare rs pin
  GPIO.output(this.__pins['rs'], int(bits[0]))
  
  if this.__bit_mode == 4:
    __instruct_4_bit_mode(bits)
  else:
    __instruct_8_bit_mode(bits)

  sleep(0.001)


# Breaks instruction to two and send it to the controller
# 4 bits at a time  
def __instruct_4_bit_mode(bits):

  for i in range(2,6):
    GPIO.output(this.__pins['db'][i-2], int(bits[i]))

  __signal_enable()

  for i in range(6,10):
    GPIO.output(this.__pins['db'][i-6], int(bits[i]))

  __signal_enable()


# Sends the whole instruction to the controller
def __instruct_8_bit_mode(bits):
  for i in range(2,10):
    GPIO.output(this.__pins['db'][i-2], int(bits[i]))

  __signal_enable()

