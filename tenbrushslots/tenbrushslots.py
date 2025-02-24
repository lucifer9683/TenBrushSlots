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

    def __init__(self):
        self.active = True
        self.erase = {}
        self.size = {}
        self.opacity = {}
        self.flow = {}
        self.rotation = {}
        self.blending = {}

    def isStateSame(self, kit: str, id: int, state: int):
        option = id % 7
        slot = int(((id - option) / 7) - 1)
        if 0 <= slot <= 9:
            match option:
                case 1:
                    return self.erase[kit][slot] == state
                case 2:
                    return self.size[kit][slot] == state
                case 3:
                    return self.opacity[kit][slot] == state
                case 4:
                    return self.flow[kit][slot] == state
                case 5:
                    return self.rotation[kit][slot] == state
                case 6:
                    return self.blending[kit][slot] == state

    def isKitStored(self, kit: str):
        return all([kit in self.erase, kit in self.size, kit in self.opacity, 
                    kit in self.flow, kit in self.rotation, kit in self.blending])
    
    def newKit(self, kit: str):
        setting = []
        for _ in range(10):
            setting.append(2)
        self.erase[kit] = setting.copy()
        self.size[kit] = setting.copy()
        self.opacity[kit] = setting.copy()
        self.flow[kit] = setting.copy()
        self.rotation[kit] = setting.copy()
        self.blending[kit] = setting.copy()

    def removeKit(self, kit: str):
        return [self.erase.pop(kit), self.size.pop(kit), self.opacity.pop(kit), 
                self.flow.pop(kit), self.rotation.pop(kit), self.blending.pop(kit)]

    def renameKit(self, prevName: str, newName: str):
        settings = self.removeKit(prevName)
        self.erase[newName] = settings[0]
        self.size[newName] = settings[1]
        self.opacity[newName] = settings[2]
        self.flow[newName] = settings[3]
        self.rotation[newName] = settings[4]
        self.blending[newName] = settings[5]

    def changeSettings(self, kit: str, ids, states):
        for index, id in enumerate(ids):
            option = id % 7
            slot = int(((id - option) / 7) - 1)
            if 0 <= slot <= 9:
                match option:
                    case 1:
                        self.erase[kit][slot] = states[index]
                    case 2:
                        self.size[kit][slot] = states[index]
                    case 3:
                        self.opacity[kit][slot] = states[index]
                    case 4:
                        self.flow[kit][slot] = states[index]
                    case 5:
                        self.rotation[kit][slot] = states[index]
                    case 6:
                        self.blending[kit][slot] = states[index]

    def getSettings(self, kit: str):
        return [self.erase[kit], self.size[kit], self.opacity[kit], 
                self.flow[kit], self.rotation[kit], self.blending[kit]]

    def getString(self, kit: str):
        ids = []
        states = []
        for index, state in enumerate(self.erase[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 1))
                states.append(str(state))
        for index, state in enumerate(self.size[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 2))
                states.append(str(state))
        for index, state in enumerate(self.opacity[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 3))
                states.append(str(state))
        for index, state in enumerate(self.flow[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 4))
                states.append(str(state))
        for index, state in enumerate(self.rotation[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 5))
                states.append(str(state))
        for index, state in enumerate(self.blending[kit]):
            if state != 2:
                ids.append(str((index + 1) * 7 + 6))
                states.append(str(state))
        return ";".join([",".join(ids), ",".join(states)]) 


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
        # Parameters to activate previous preset and next group/position
        self.activatePrev = True
        self.activateNext = True
        self.nextGroup = True
        self.prevPreset = []
        self.prevSlot = []
        # Parameters for auto brush tool
        self.autoBrush = True
        self.brushTool = None
        # Sync preset settings when cycling in slot
        self.sync = SlotSync()
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
        notify.windowCreated.connect(self.newWindow)
        notify.imageClosed.connect(self.resetCurrent)
        notify.setActive(True)

    def newWindow(self):
        windows = Application.windows()
        windows[-1].windowClosed.connect(self.resetPointers)
        self.loadTool()
        self.resetCurrent()

    def resetCurrent(self):
        if Application.activeWindow().views():
            return
        
        preset = Application.readSetting("", "LastPreset", "")
        allPresets = Application.resources('preset')
        if preset in allPresets:
            window = list(Application.windows()).index(Application.activeWindow())
            slot = self.findPreset(preset, window)
            if slot is not None:
                self.currentSlot[window] = slot

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

        preset = Application.readSetting("", "LastPreset", "")
        view = Application.activeWindow().activeView()
        if view.visible():
            preset = view.currentBrushPreset().name()

        currentSlot = None
        allPresets = Application.resources('preset')
        if preset in allPresets:
            currentSlot = self.findPreset(preset, window)
            if currentSlot is not None:
                self.currentSlot[window] = currentSlot

        prevSlot = None
        if self.prevPreset[window]:
            preset = self.prevPreset[window].name()
            if preset in allPresets:
                prevSlot = self.findPreset(preset, window, currentSlot)
                if prevSlot is not None:
                    self.prevSlot[window] = prevSlot

        start = window * ACTIONS
        for index, action in enumerate(self.actions[start:start+len(SLOTS)]):
            if index == currentSlot or index == prevSlot:
                continue
            
            if self.kits[kit][index]:
                action.preset = ActionPreset(0, self.kits[kit][index][0][0])
            else:
                action.preset = None

    def findPreset(self, presetName: str, window: int, currentSlot=None):
        presetSlot = None
        presetGroup = 0
        for index, slot in enumerate(self.kits[self.activeKit[window]]):
            if presetSlot is not None:
                    break

            for idx, group in enumerate(slot):
                if presetName in group:
                    presetSlot = index
                    presetGroup = idx
                    break
        if presetSlot is not None and presetSlot != currentSlot:
            self.actions[presetSlot + window*ACTIONS].preset = ActionPreset(presetGroup, presetName)
        return presetSlot
    
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

            self.sync.newKit(kit)
            sync = Application.readSetting(MENU_ENTRY, f"{index}sync", "").split(";")
            if len(sync) == 2:
                ids = [int(id) for id in sync[0].split(",") if id.isdecimal()]
                states = [int(state) for state in sync[1].split(",") if state == "0" or state == "1"]
                if len(ids) == len(states):
                    self.sync.changeSettings(kit, ids, states)

        options = Application.readSetting(MENU_ENTRY, "options", "").split(",")
        if len(options) == 5:
            self.activatePrev = options[0] == "True"
            self.activateNext = options[1] == "True"
            self.nextGroup = options[2] == "True"
            self.autoBrush = options[3] == "True"
            self.sync.active = options[4] == "True"

    def writeSettings(self):
        kits = list(self.kits.keys())
        Application.writeSetting(MENU_ENTRY, "kits", ",".join(kits))

        for index, kit in enumerate(self.kits):
            for idx, number in enumerate(SLOTS):
                slot = [",".join(group) for group in self.kits[kit][idx]]
                Application.writeSetting(MENU_ENTRY, f"{index}slot{number}", ";".join(slot))

            Application.writeSetting(MENU_ENTRY, f"{index}sync", self.sync.getString(kit))

        options = []
        options.append(str(self.activatePrev))
        options.append(str(self.activateNext))
        options.append(str(self.nextGroup))
        options.append(str(self.autoBrush))
        options.append(str(self.sync.active))
        Application.writeSetting(MENU_ENTRY, "options", ",".join(options))
    
    def loadActions(self, window):
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
        preset: ActionPreset = self.sender().preset
        if preset is None:
            self.showMessage(view, window, 'empty')
            return
            
        allPresets = Application.resources('preset')
        if preset.name not in allPresets:
            self.showMessage(view, window, 'missing')
            return

        # Multiple windows will append another set of actions to the list
        slot = self.actions.index(self.sender()) % ACTIONS
        currentPreset = view.currentBrushPreset()
        if preset.name == currentPreset.name() and (not self.autoBrush or self.brushTool.isChecked()):
            kit = self.activeKit[window]
            if self.activateNext and self.nextGroup and len(self.kits[kit][slot]) > 1:
                self.currentSlot[window] = slot
                if not self.cycleGroup(view, allPresets, preset, ActionCycle.Value, window):
                    self.showMessage(view, window, 'missing')
                    return
            elif self.activateNext and (not self.nextGroup and 
                                        len(self.kits[kit][slot][preset.group]) > 1):
                self.currentSlot[window] = slot
                if not self.cyclePosition(view, allPresets, preset, ActionCycle.Value, window):
                    self.showMessage(view, window, 'missing')
                    return
            elif self.activatePrev and self.prevPreset[window] is not None:
                synced = False
                prevName = self.prevPreset[window].name()
                if self.currentSlot[window] != self.prevSlot[window]:
                    if slot == self.currentSlot[window]:
                        for group in self.kits[kit][self.prevSlot[window]]:
                            if prevName in group:
                                self.currentSlot[window] = self.prevSlot[window]
                                self.prevSlot[window] = slot
                                break
                    else:
                        for group in self.kits[kit][self.currentSlot[window]]:
                            if prevName in group:
                                self.prevSlot[window] = slot
                                break
                else:
                    for index, group in enumerate(self.kits[kit][slot]):
                        if prevName in group:
                            self.actions[slot + window*ACTIONS].preset = ActionPreset(index, prevName)
                            synced = self.activateAndSync(view, allPresets, prevName, window, index == preset.group)
                            break
                if not synced:
                    view.activateResource(self.prevPreset[window])
                self.prevPreset[window] = currentPreset
        else:
            if preset.name != currentPreset.name():
                self.prevPreset[window] = currentPreset
                self.prevSlot[window] = self.currentSlot[window]
            self.currentSlot[window] = slot
            view.activateResource(allPresets[preset.name])

        if self.autoBrush:
            Application.action('KritaShape/KisToolBrush').trigger()
        self.showMessage(view, window, 'selected')
    
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

        currentSlot = self.currentSlot[window]
        preset: ActionPreset = self.actions[currentSlot + window*ACTIONS].preset
        changed = False
        if preset is None:
            currentSlot = self.findPreset(currentPreset.name(), window)
            changed = True
        else:
            currentPreset = view.currentBrushPreset()
            if preset.name != currentPreset.name():
                currentSlot = self.findPreset(currentPreset.name(), window)
                changed = True

        if currentSlot is not None:
            if changed:
                preset = self.actions[currentSlot + window*ACTIONS].preset
                self.currentSlot[window] = currentSlot
            
            allPresets = Application.resources('preset')
            slot = self.kits[self.activeKit[window]][currentSlot]
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
        currentSlot = self.currentSlot[window]
        slot = self.kits[self.activeKit[window]][currentSlot]
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
            self.actions[currentSlot + window*ACTIONS].preset = ActionPreset(destination, presetName)
            self.prevPreset[window] = view.currentBrushPreset()
            self.prevSlot[window] = currentSlot
            return self.activateAndSync(view, allPresets, presetName, window)

    def cyclePosition(self, view, allPresets: dict, preset: ActionPreset, vector: int, window: int):
        currentSlot = self.currentSlot[window]
        slot = self.kits[self.activeKit[window]][currentSlot]
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
            self.actions[currentSlot + window*ACTIONS].preset = ActionPreset(preset.group, presetName)
            self.prevPreset[window] = view.currentBrushPreset()
            self.prevSlot[window] = currentSlot
            return self.activateAndSync(view, allPresets, presetName, window, True)
        
    def activateAndSync(self, view, allPresets: dict, presetName: str, window: int, sameGroup=False):
        erase = Application.action('erase_action')
        state = erase.isChecked()
        size = view.brushSize()
        opacity = view.paintingOpacity()
        flow = view.paintingFlow()
        rotation = view.brushRotation()
        blending = view.currentBlendingMode()

        view.activateResource(allPresets[presetName])
        if self.sync.active:
            kit = self.activeKit[window]
            slot = self.currentSlot[window]

            if self.sync.erase[kit][slot] == 2 or (self.sync.erase[kit][slot] == 1 and sameGroup):
                if state != erase.isChecked():
                    erase.trigger()
            if self.sync.size[kit][slot] == 2 or (self.sync.size[kit][slot] == 1 and sameGroup):
                view.setBrushSize(size)
            if self.sync.opacity[kit][slot] == 2 or (self.sync.opacity[kit][slot] == 1 and sameGroup):
                view.setPaintingOpacity(opacity)
            if self.sync.flow[kit][slot] == 2 or (self.sync.flow[kit][slot] == 1 and sameGroup):
                view.setPaintingFlow(flow)
            if self.sync.rotation[kit][slot] == 2 or (self.sync.rotation[kit][slot] == 1 and sameGroup):
                view.setBrushRotation(rotation)
            if self.sync.blending[kit][slot] == 2 or (self.sync.blending[kit][slot] == 1 and sameGroup):
                view.setCurrentBlendingMode(blending)

        return True

