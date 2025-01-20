# SPDX-License-Identifier: GPL-3.0-or-later
#
# Ten Brush Slots is a Krita plugin for switching brush presets.
# Copyright (C) 2023  Lucifer <krita-artists.org/u/Lucifer>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QDockWidget, QToolButton
from krita import Extension

from .sloteditor import SlotEditor

EXTENSION_ID = "pykrita_tenbrushslots"
MENU_ENTRY = i18n("Ten Brush Slots")
SLOTS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
# Amount of actions appended to self.actions list per window
ACTIONS = 16
# Floating message duration in ms
TIME = 1000


class ActionPreset:

    def __init__(self, group: int, name: str):
        self.group = group
        self.name = name


class ActionCycle:
    
    Orders = ['kit', 'group', 'position']
    Moves = ['next', 'previous']
    Value = 1

    def __init__(self, order: str, move: str):
        self.order = order
        self.vector = self.moveToVector(move)

    def moveToVector(self, move) -> int:
        if move == 'next':
            return self.Value
        elif move == 'previous':
            return -(self.Value)
        

class SlotSync:

    def __init__(self, active=False, size=True, opacity=True, flow=True, erase=True):
        self.active = active
        self.size = size
        self.opacity = opacity
        self.flow = flow
        self.erase = erase


class TenBrushSlots(Extension):

    def __init__(self, parent):
        super().__init__(parent)

        # All presets chosen by user
        self.kits = {}
        # Current kit/slot for switching presets
        self.activeKit = []
        self.currentSlot = []
        # Store parameters to shortcuts
        self.actions = []
        # Parameters to activate previous slot/preset
        self.activatePrev = True
        self.enforcePrev = False
        self.prevPreset = []
        self.prevSlot = []
        # Parameters for auto brush tool
        self.autoBrush = True
        self.brushTool = None
        # Sync preset settings when cycling in slot
        self.sync = SlotSync(True)
        # Checks if editor updated slots/settings
        self.kitsEdited = []
        self.updateSettings = False
        # delay 10ms as closed window yet to be destroyed when signal emitted 
        self.waitToRemove = QTimer()
        self.waitToRemove.setSingleShot(True)
        self.waitToRemove.timeout.connect(self.removeActions)
    
    def setup(self):
        self.readSettings()
        notify = Application.notifier()
        notify.setActive(True)
        notify.windowCreated.connect(self.newWindow)

    def newWindow(self):
        windows = Application.windows()
        windows[-1].windowClosed.connect(self.resetPointers)
        self.loadTool()

    def resetPointers(self):
        if Application.windows():
            self.loadTool()
            self.waitToRemove.start(10)

    def loadTool(self):    
        toolBox = Application.activeWindow().qwindow().findChild(QDockWidget, 'ToolBox')
        self.brushTool = toolBox.findChild(QToolButton, 'KritaShape/KisToolBrush')

    def createActions(self, window):
        action = window.createAction(EXTENSION_ID, MENU_ENTRY, "tools/scripts")
        action.setToolTip(i18n("Assign brush presets to ten configurable slots."))
        action.triggered.connect(self.openEditor)
        self.loadActions(window)

    def openEditor(self):
        window = list(Application.windows()).index(Application.activeWindow())
        mainDialog = SlotEditor(MENU_ENTRY, window, self)
        mainDialog.exec()
        if self.updateSettings or self.kitsEdited:
            self.writeSettings()
            self.updateSettings = False
            self.kitsEdited = []

    def reorderKits(self, kitOrder: list):
        orderedKits = {}
        for kit in kitOrder:
            orderedKits[kit] = self.kits.pop(kit)
        self.kits = orderedKits
        self.updateSettings = True

    def updateName(self, prevName: str, newName: str):
        self.kits[newName] = self.kits.pop(prevName)
        for index, kit in enumerate(self.activeKit):
            if kit == prevName:
                self.activeKit[index] = newName
        if prevName in self.kitsEdited:
            self.kitsEdited.remove(prevName)
            self.kitsEdited.append(newName)
        self.updateSettings = True

    def updateKit(self, kit: str, slots: list):
        self.kits[kit] = slots
        if kit not in self.kitsEdited:
            self.kitsEdited.append(kit)

    def removeKit(self, kit: str):
        if kit in self.kits:
            self.kits.pop(kit)
            self.updateSettings = True

        if not self.kits:
            kit = ""
            self.kits[kit] = []
            if kit not in self.kitsEdited:
                self.kitsEdited.append(kit)
    
    def setActiveKit(self, kit: str, window: int):
        self.activeKit[window] = kit
        start = window * ACTIONS
        for index, action in enumerate(self.actions[start:start+len(SLOTS)]):
            action.preset = None
            if self.kits[kit][index]:
                action.preset = ActionPreset(0, self.kits[kit][index][0][0])
    
    def readSettings(self):
        allPresets = Application.resources('preset')
        kits = Application.readSetting(MENU_ENTRY, "kits", "").split(",")
        for index, kit in enumerate(kits):
            self.kits[kit] = []

            for number in SLOTS:
                slot = Application.readSetting(MENU_ENTRY, f"{index}slot{number}", "").split(";")

                for idx, string in enumerate(slot):
                    slot[idx] = [name for name in string.split(",") if name in allPresets]
                
                slot = [group for group in slot if group]
                self.kits[kit].append(slot)

        options = Application.readSetting(MENU_ENTRY, "options", "").split(",")
        if len(options) == 8:
            self.activatePrev = options[0] == "True"
            self.enforcePrev = options[1] == "True"
            self.autoBrush = options[2] == "True"
            self.sync.active = options[3] == "True"
            self.sync.size = options[4] == "True"
            self.sync.opacity = options[5] == "True"
            self.sync.flow = options[6] == "True"
            self.sync.erase = options[7] == "True"

    def writeSettings(self):
        kits = list(self.kits.keys())
        Application.writeSetting(MENU_ENTRY, "kits", ",".join(kits))

        for index, kit in enumerate(self.kits):
            for idx, number in enumerate(SLOTS):
                slot = [",".join(group) for group in self.kits[kit][idx]]
                Application.writeSetting(MENU_ENTRY, f"{index}slot{number}", ";".join(slot))

        options = []
        options.append(str(self.activatePrev))
        options.append(str(self.enforcePrev))
        options.append(str(self.autoBrush))
        options.append(str(self.sync.active))
        options.append(str(self.sync.size))
        options.append(str(self.sync.opacity))
        options.append(str(self.sync.flow))
        options.append(str(self.sync.erase))
        Application.writeSetting(MENU_ENTRY, "options", ",".join(options))
    
    def loadActions(self, window) -> None:
        kit = list(self.kits.keys())[0]
        for index, number in enumerate(SLOTS):
            action = window.createAction(f"activate_slot_{number}", i18n(f"Activate Brush Slot {number}"), "")
            action.triggered.connect(self.activateSlot)

            action.preset = None
            if self.kits[kit][index]:
                action.preset = ActionPreset(0, self.kits[kit][index][0][0])
            self.actions.append(action)

        for order in ActionCycle.Orders:
            for move in ActionCycle.Moves:
                action = window.createAction(f"switch_to_{move}_{order}", 
                                             i18n(f"Switch To {move.capitalize()} {order.capitalize()}"), "")
                action.triggered.connect(self.switchPreset)

                action.cycle = ActionCycle(order, move)
                self.actions.append(action)
        
        # Each window to have their own kit/slot/preset memory
        self.activeKit.append(kit)
        self.currentSlot.append(0)
        self.prevSlot.append(0)
        self.prevPreset.append(None)

    def removeActions(self):
        removing = []
        for index, action in enumerate(self.actions):
                try:
                    action.parent()
                except RuntimeError:
                    removing.append(index)
        for id in reversed(removing):
            self.actions.pop(id)
        
        # Remove kit/slot/preset memory of closed windows
        for id in reversed(removing[::ACTIONS]):
            window = int(id / ACTIONS)
            self.activeKit.pop(window)
            self.currentSlot.pop(window)
            self.prevSlot.pop(window)
            self.prevPreset.pop(window)

    def activateSlot(self):
        view = Application.activeWindow().activeView()
        if not view.visible():
            return
        
        window = int(self.actions.index(self.sender()) / ACTIONS)
        preset = self.sender().preset
        if preset is None:
            self.showMessage(view, window, 'empty')
            return
            
        allPresets = Application.resources('preset')
        if  preset.name not in allPresets:
            self.showMessage(view, window, 'missing')
            return

        # Multiple windows will append another set of actions to the list
        slot = self.actions.index(self.sender()) % ACTIONS
        currentPreset = view.currentBrushPreset()
        if preset.name == currentPreset.name() and (not self.autoBrush or self.brushTool.isChecked()):
            if len(self.kits[self.activeKit[window]][slot]) > 1 and not(self.activatePrev and self.enforcePrev):
                self.currentSlot[window] = slot
                if not self.cycleGroup(view, allPresets, preset, ActionCycle.Value, window):
                    self.showMessage(view, window, 'missing')
                    return
            elif self.activatePrev and self.prevPreset[window] is not None:
                if self.currentSlot[window] != self.prevSlot[window]:
                    self.setPrevSlot(slot, window)
                view.activateResource(self.prevPreset[window])
                self.prevPreset[window] = currentPreset
        else:
            if preset.name != currentPreset.name() or not self.autoBrush:
                self.prevPreset[window] = currentPreset
                self.prevSlot[window] = self.currentSlot[window]
            self.currentSlot[window] = slot
            view.activateResource(allPresets[preset.name])

        if self.autoBrush:
            Application.action('KritaShape/KisToolBrush').trigger()
        self.showMessage(view, window, 'selected')

    def setPrevSlot(self, slot: int, window:int):
        if slot == self.currentSlot[window]:
            for group in self.kits[self.activeKit[window]][self.prevSlot[window]]:
                if self.prevPreset[window].name() in group:
                    self.currentSlot[window] = self.prevSlot[window]
                    self.prevSlot[window] = slot
                    return self.prevSlot[window]
        else:
            for group in self.kits[self.activeKit[window]][self.currentSlot[window]]:
                if self.prevPreset[window].name() in group:
                    self.prevSlot[window] = slot
                    return self.prevSlot[window]
    
    def showMessage(self, view, window: int, message: str):
        kit = self.activeKit[window]
        activePreset = view.currentBrushPreset()

        if message == 'selected':
            view.showFloatingMessage(i18n("{}\nselected")
                                     .format(f"{kit}: {activePreset.name()}" if kit else activePreset.name()), 
                                     QIcon(QPixmap.fromImage(activePreset.image())), TIME, 1)
        elif message == 'missing':
            view.showFloatingMessage(i18n("{}Missing Preset").format(f"{kit}: " if kit else ""), 
                                     Application.icon('warning'), TIME, 1)
        elif message == 'empty':
            view.showFloatingMessage(i18n("{}Empty Slot").format(f"{kit}: " if kit else ""), 
                                     Application.icon('warning'), TIME, 1)
        elif message == 'kit':
            view.showFloatingMessage(i18n("{}Kit\nselected").format(f"{kit} " if kit else ""), 
                                     Application.icon('krita_tool_freehand'), TIME, 1)

    def switchPreset(self):
        view = Application.activeWindow().activeView()
        if not view.visible():
            return
        
        window = int(self.actions.index(self.sender()) / ACTIONS)
        cycle = self.sender().cycle
        if cycle.order == 'kit':
            if len(self.kits) > 1:
                self.cycleKit(cycle.vector, window)
                self.showMessage(view, window, 'kit')
            return
        
        preset = self.actions[self.currentSlot[window] + window*ACTIONS].preset
        if preset is None:
            self.showMessage(view, window, 'empty')
            return
        
        allPresets = Application.resources('preset')
        slot = self.kits[self.activeKit[window]][self.currentSlot[window]]
        if cycle.order == 'group' and len(slot) > 1:
            if not self.cycleGroup(view, allPresets, preset, cycle.vector, window):
                self.showMessage(view, window, 'missing')
                return
        elif cycle.order == 'position' and len(slot[preset.group]) > 1:
            if not self.cyclePosition(view, allPresets, preset, cycle.vector, window):
                self.showMessage(view, window, 'missing')
                return

        if self.autoBrush:
            Application.action('KritaShape/KisToolBrush').trigger()
        self.showMessage(view, window, 'selected')

    def getDestination(self, start: int, length: int, vector: int):
        destination = start + vector
        while destination < 0 or destination >= length:
            if destination < 0:
                destination = destination + length
            else:
                destination = destination - length
        return destination

    def cycleKit(self, vector: int, window: int):
        kits = list(self.kits.keys())
        index = kits.index(self.activeKit[window])
        destination = self.getDestination(index, len(kits), vector)
        self.setActiveKit(kits[destination], window)
    
    def cycleGroup(self, view, allPresets: dict, preset: ActionPreset, vector: int, window: int):
        slot = self.kits[self.activeKit[window]][self.currentSlot[window]]
        if not slot or preset.group >= len(slot):
            return
        
        try:
            position = slot[preset.group].index(preset.name)
        except ValueError:
            return
        
        destination = self.getDestination(preset.group, len(slot), vector)
        if position >= len(slot[destination]):
            position = 0

        presetName = slot[destination][position]
        if presetName in allPresets:
            self.actions[self.currentSlot[window] + window*ACTIONS].preset = ActionPreset(destination, presetName)
            self.prevPreset[window] = view.currentBrushPreset()
            self.prevSlot[window] = self.currentSlot[window]
            return self.activateAndSync(view, allPresets, presetName, window)

    def cyclePosition(self, view, allPresets: dict, preset: ActionPreset, vector: int, window: int):
        slot = self.kits[self.activeKit[window]][self.currentSlot[window]]
        if not slot or preset.group >= len(slot):
            return
        
        group = slot[preset.group]
        try:
            position = group.index(preset.name)
        except ValueError:
            return

        destination = self.getDestination(position, len(group), vector)
        presetName = group[destination]
        if presetName in allPresets:
            self.actions[self.currentSlot[window] + window*ACTIONS].preset = ActionPreset(preset.group, presetName)
            self.prevPreset[window] = view.currentBrushPreset()
            self.prevSlot[window] = self.currentSlot[window]
            return self.activateAndSync(view, allPresets, presetName, window)
        
    def activateAndSync(self, view, allPresets: dict, presetName: str, window: int):
        size = view.brushSize()
        opacity = view.paintingOpacity()
        flow = view.paintingFlow()
        erase = Application.action('erase_action')
        state = erase.isChecked()

        view.activateResource(allPresets[presetName])
        if self.sync.active:
            if self.sync.size:
                view.setBrushSize(size)
            if self.sync.opacity:
                view.setPaintingOpacity(opacity)
            if self.sync.flow:
                view.setPaintingFlow(flow)
            if self.sync.erase:
                if state != erase.isChecked():
                    erase.trigger()
        return presetName

