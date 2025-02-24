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

from typing import List, Dict
from PyQt5.QtCore import Qt, QSize, QItemSelectionModel
from PyQt5.QtGui import QPixmap, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListView, 
                             QStyleOptionViewItem, QPushButton, QMessageBox, QCheckBox, 
                             QGroupBox, QGridLayout, QComboBox, QListWidget, QRadioButton)
from krita import PresetChooser

ICON_WIDTH = 64
ICON_HEIGHT = 64
ICON_SIZE = QSize(ICON_WIDTH, ICON_HEIGHT)


class SlotView(QListView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMovement(QListView.Movement.Snap)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setAutoScrollMargin(ICON_HEIGHT)
        self.setAutoScroll(True)
        self.horizontalScrollBar().setEnabled(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.setIconSize(ICON_SIZE)
        self.setGridSize(ICON_SIZE)
        # View width should be fixed at 2px more than icon width for perfect fit
        self.setFixedWidth(ICON_WIDTH + 2)
        # Icons should not fit vertically if items exceed initial viewport size
        self.setMinimumHeight(int(ICON_HEIGHT * 4.5))

    def viewOptions(self):
        option = super().viewOptions()
        option.showDecorationSelected = True
        option.decorationPosition = QStyleOptionViewItem.Position.Top
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter
        return option
    
    def enterEvent(self, event):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        super().leaveEvent(event)


class ChoiceDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.editor = parent
        self.setWindowTitle(i18n("Preset Chooser"))
        self.mainLayout = QVBoxLayout(self)
        self.presetChooser = PresetChooser()
        self.presetChooser.presetClicked.connect(self.checkPreset)
        self.mainLayout.addWidget(self.presetChooser)
    
    def checkPreset(self):
        preset = self.presetChooser.currentPreset()
        if "," in preset.name() or ";" in preset.name():
            QMessageBox().warning(self, i18n("Preset Chooser"), 
            i18n("Unable to read commas( , ) and semicolons( ; ).\n\nPlease rename this preset before adding."))
        else:
            self.accept(preset)

    def accept(self, preset):
        self.editor.chosenPreset = preset
        super().accept()


class SyncConfig(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.editor = parent
        self.setWindowTitle(i18n("Configure Syncing"))
        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)
        
        self.kitList = QListWidget()
        for index in range(self.editor.kitBox.count()):
            self.kitList.addItem(self.editor.kitBox.itemText(index))
        self.kitList.setCurrentRow(0)
        self.kitList.currentItemChanged.connect(self.switchKit)
        self.kitList.setFixedWidth(128)
        self.mainLayout.addWidget(self.kitList)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(16)
        self.mainLayout.addLayout(self.grid)

        self.gridButton(i18n("&Settings / Slots"), 0, 0)
        self.gridButton(i18n("&Erase Mode"), 1, 0)
        self.gridButton(i18n("&Brush Size"), 2, 0)
        self.gridButton(i18n("Painting &Opacity"), 3, 0)
        self.gridButton(i18n("Painting &Flow"), 4, 0)
        self.gridButton(i18n("Brush &Rotation"), 5, 0)
        self.gridButton(i18n("Blending &Mode"), 6, 0)

        for index in range(10):
            action = self.editor.ten.actions[index]
            self.gridButton(action.shortcut().toString(), 0, index + 1)
            for i in range(self.grid.rowCount() - 1):
                box = QCheckBox()
                box.setTristate(True)
                box.setToolTip(i18n("If Partially Checked, Only Presets in the Same Group Will Be Synced"))
                box.stateChanged.connect(self.setEdited)
                self.grid.addWidget(box, i + 1, index + 1)
                self.grid.setAlignment(box, Qt.AlignmentFlag.AlignCenter)

        self.edited = []
        self.loadSettings(self.kitList.currentItem().text())

    def gridButton(self, text: str, row: int, column: int):
        button = QPushButton(text)
        button.setAutoDefault(False)
        name = f"Slot {text}" if "&" not in text else text.translate(str.maketrans("", "", "&"))
        button.setToolTip(i18n(f"Check/Uncheck All in {name}"))
        button.clicked.connect(self.checkAll)
        if column > 0 and len(text) == 1:
            button.setFixedWidth(36)
        self.grid.addWidget(button, row, column)

    def checkAll(self):
        id = self.grid.indexOf(self.sender())
        rows = self.grid.rowCount()
        if id < rows:
            if id == 0:
                count = self.grid.count()
                state = self.allState(count)
                for i in range(rows + 1, count):
                    box = self.grid.itemAt(i).widget()
                    if type(box) is not QCheckBox:
                        continue
                    box.setCheckState(state)
            else:
                state = self.allState(10, id)
                for i in range(10):
                    box = self.grid.itemAtPosition(id, i + 1).widget()
                    box.setCheckState(state)
        else:
            id = int(id / rows)
            state = self.allState(rows - 1, id)
            for i in range(rows - 1):
                box = self.grid.itemAtPosition(i + 1, id).widget()
                box.setCheckState(state)

    def allState(self, count: int, id=0):
        high = 0
        low = 2
        for i in range(count):
            box = None
            if count > 10:
                box = self.grid.itemAt(i).widget()
            elif count == 10:
                box = self.grid.itemAtPosition(id, i + 1).widget()
            else:
                box = self.grid.itemAtPosition(i + 1, id).widget()
            
            if type(box) is not QCheckBox:
                continue
            
            state = box.checkState()
            if state > high:
                high = state
            if state < low:
                low = state
            if high == 2 and low < 2:
                break
        if high == low:
            if high == 2:
                high = 0
            else:
                high += 1
        return high

    def loadSettings(self, kit: str):
        settings = self.editor.ten.sync.getSettings(kit)
        for i, setting in enumerate(settings):
            for j, state in enumerate(setting):
                box = self.grid.itemAtPosition(i + 1, j + 1).widget()
                box.setCheckState(state)
        self.edited = []

    def saveSettings(self, kit: str):
        states = []
        for id in self.edited:
            box = self.grid.itemAt(id).widget()
            states.append(box.checkState())
        if len(self.edited) == len(states):
            self.editor.ten.sync.changeSettings(kit, self.edited, states)
            self.editor.ten.updateSettings = True

    def setEdited(self, state):
        id = self.grid.indexOf(self.sender())
        same = self.editor.ten.sync.isStateSame(self.kitList.currentItem().text(), id, state)
        if same and id in self.edited:
            self.edited.remove(id)
        elif not same and id not in self.edited:
            self.edited.append(id)
    
    def switchKit(self, current, previous):
        if self.edited:
            self.saveSettings(previous.text())
        self.loadSettings(current.text())

    def closeEvent(self, event):
        if self.edited:
            self.saveSettings(self.kitList.currentItem().text())
        event.accept()


class PresetItem(QStandardItem):

    def __init__(self, icon: QIcon, tooltip: str, parent=None):
        super().__init__(parent)

        self.setIcon(icon)
        self.setToolTip(tooltip)
        self.setSizeHint(ICON_SIZE)
        self.setEditable(False)
        self.setDropEnabled(False)


class DividerItem(QStandardItem):

    Name = i18n("Group Divider")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setIcon(Application.icon('curve-preset-linear'))
        self.setToolTip(self.Name)
        self.setStatusTip(self.Name)
        self.setSizeHint(ICON_SIZE)
        self.setEditable(False)
        self.setDropEnabled(False)


class SlotElements:

    def __init__(self):
        self.models: List[QStandardItemModel] = []
        self.views: List[SlotView] = []
        self.addButtons: List[QPushButton] = []
        self.grpButtons: List[QPushButton] = []
        self.delButtons: List[QPushButton] = []
        self.presets: Dict[str, int] = {}
        self.shortcuts: List[str] = []

    def label(self, shortcut: str):
        label = QLabel(shortcut)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.shortcuts.append(shortcut)
        return label

    def modelView(self):
        view = SlotView()
        model = QStandardItemModel()
        view.setModel(model)
        self.models.append(model)
        self.views.append(view)
        return view

    def addButton(self, slot):
        button = QPushButton()
        button.setAutoDefault(False)
        button.setIcon(Application.icon('addlayer'))
        to_slot = ""
        if self.shortcuts:
            index = len(self.shortcuts) - 1
            to_slot = i18n(f" to Slot {self.shortcuts[index]}")
        button.setToolTip(i18n(f"Add Brush Preset{to_slot}"))
        button.clicked.connect(slot)
        self.addButtons.append(button)
        return button
    
    def grpButton(self, slot):
        button = QPushButton()
        button.setAutoDefault(False)
        button.setIcon(Application.icon('groupLayer'))
        to_slot = ""
        if self.shortcuts:
            index = len(self.shortcuts) - 1
            to_slot = i18n(f" to Slot {self.shortcuts[index]}")
        button.setToolTip(i18n(f"Add Group Divider{to_slot}"))
        button.clicked.connect(slot)
        self.grpButtons.append(button)
        return button
    
    def delButton(self, slot):
        button = QPushButton()
        button.setAutoDefault(False)
        button.setIcon(Application.icon('deletelayer'))
        in_slot = ""
        if self.shortcuts:
            index = len(self.shortcuts) - 1
            in_slot = i18n(f" in Slot {self.shortcuts[index]}")
        button.setToolTip(i18n(f"Delete Selected Items{in_slot}"))
        button.clicked.connect(slot)
        self.delButtons.append(button)
        return button
    
    def clear(self):
        for model in self.models:
            model.clear()
        self.presets = {}


class SlotEditor(QDialog):
    
    def __init__(self, title: str, window: int, extension, parent=None):
        super().__init__(parent)

        self.ten = extension
        self.chosenPreset = None
        self.mainLayout = QVBoxLayout(self)
        self.setWindowTitle(title)
        self.windex = window
        self.loadKits()
        self.mainLayout.addSpacing(4)
        self.loadSlots()
        self.mainLayout.addSpacing(8)
        self.loadOptions()
        self.setFocus()

    def loadKits(self):
        self.kitBox = QComboBox()
        self.kitBox.addItems(self.ten.kits.keys())
        self.kitBox.setEditable(True)
        self.kitBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.kitBox.setMinimumWidth(240)
        self.kitBox.setCurrentIndex(self.kitBox.findText(self.ten.activeKit[self.windex]))
        self.currentText = self.kitBox.currentText()
        self.prevText = self.currentText
        self.kitBox.editTextChanged.connect(self.setPrevText)
        self.currentIndex = self.kitBox.currentIndex()
        self.prevIndex = self.currentIndex
        self.kitBox.currentIndexChanged.connect(self.selectKit)

        newKit = QPushButton()
        newKit.setAutoDefault(False)
        newKit.setIcon(Application.icon('addlayer'))
        newKit.setToolTip(i18n("Add New Kit"))
        newKit.clicked.connect(self.newKit)

        moveUp = QPushButton()
        moveUp.setAutoDefault(False)
        moveUp.setIcon(Application.icon('arrow-up'))
        moveUp.setToolTip(i18n("Move Up Selected Kit"))
        moveUp.clicked.connect(self.moveKit)

        moveDown = QPushButton()
        moveDown.setAutoDefault(False)
        moveDown.setIcon(Application.icon('arrow-down'))
        moveDown.setToolTip(i18n("Move Down Selected Kit"))
        moveDown.clicked.connect(self.moveKit)
        
        deleteKit = QPushButton()
        deleteKit.setAutoDefault(False)
        deleteKit.setIcon(Application.icon('deletelayer'))
        deleteKit.setToolTip(i18n("Delete Selected Kit"))
        deleteKit.clicked.connect(self.deleteKit)

        kitsLayout = QHBoxLayout()
        kitsLayout.addStretch()
        kitsLayout.addWidget(QLabel(i18n("Select Kit:")))
        kitsLayout.addWidget(self.kitBox)
        kitsLayout.addWidget(newKit)
        kitsLayout.addWidget(moveUp)
        kitsLayout.addWidget(moveDown)
        kitsLayout.addWidget(deleteKit)
        kitsLayout.addStretch()
        self.mainLayout.addLayout(kitsLayout)

    def loadSlots(self):
        self.slot = SlotElements()
        slotLayout = QHBoxLayout()
        allPresets = Application.resources('preset')
        kit = self.ten.kits[self.ten.activeKit[self.windex]]

        for index, slot in enumerate(kit):
            buttonLayout = QVBoxLayout()
            action = self.ten.actions[index]
            buttonLayout.addWidget(self.slot.label(action.shortcut().toString()))

            buttonLayout.addWidget(self.slot.modelView())
            self.loadModel(allPresets, index, slot)

            buttonLayout.addWidget(self.slot.addButton(self.insertPreset))
            buttonLayout.addWidget(self.slot.grpButton(self.insertDividers))
            buttonLayout.addWidget(self.slot.delButton(self.removeItems))

            slotLayout.addLayout(buttonLayout)
        self.mainLayout.addLayout(slotLayout)

    def loadModel(self, allPresets: dict, index: int, slot: List[List[str]]):
        model = self.slot.models[index]
        for group in slot:
            for name in group:
                if name in allPresets:
                    if name in self.slot.presets:
                        continue
                    preset = PresetItem(QIcon(QPixmap.fromImage(allPresets[name].image())), name)
                    model.appendRow(preset)
                    self.slot.presets[name] = index
            if len(slot) - slot.index(group) > 1:
                divider = DividerItem()
                model.appendRow(divider)

    def loadOptions(self):
        self.activatePrevBox = QCheckBox(i18n("Switch to Previous &Brush on 2nd Press"))
        self.activatePrevBox.setChecked(self.ten.activatePrev)

        self.activateNextBox = QGroupBox(i18n("Switch to &Next Group/Position on 2nd Press"))
        self.activateNextBox.setToolTip(
            i18n("Overrides Switch to Previous Brush if Slot Contains Multiple Groups/Presets"))
        self.activateNextBox.setCheckable(True)
        self.activateNextBox.setChecked(self.ten.activateNext)

        self.nextGroupButton = QRadioButton(i18n("&Group"))
        nextPositionButton = QRadioButton(i18n("&Position"))
        if self.ten.nextGroup:
            self.nextGroupButton.setChecked(True)
        else:
            nextPositionButton.setChecked(True)

        nextBoxLayout = QHBoxLayout()
        nextBoxLayout.addWidget(self.nextGroupButton)
        nextBoxLayout.addWidget(nextPositionButton)
        self.activateNextBox.setLayout(nextBoxLayout)

        self.autoBrushBox = QCheckBox(i18n("&Auto-Select Freehand Brush Tool"))
        self.autoBrushBox.setToolTip(i18n("Also Prevents 2nd Press Switching if Tool Not Selected"))
        self.autoBrushBox.setChecked(self.ten.autoBrush)
        
        self.syncBox = QGroupBox(i18n("&Sync Settings When Switching Group/Position"))
        self.syncBox.setCheckable(True)
        self.syncBox.setChecked(self.ten.sync.active)

        configButton = QPushButton(i18n("&Configure Syncing"))
        configButton.setAutoDefault(False)
        configButton.clicked.connect(self.openConfig)
        
        syncBoxLayout = QVBoxLayout()
        syncBoxLayout.addWidget(configButton)
        self.syncBox.setLayout(syncBoxLayout)

        optionsLayout = QGridLayout()
        optionsLayout.addWidget(self.activatePrevBox, 0, 0)
        optionsLayout.addWidget(self.activateNextBox, 1, 0)
        optionsLayout.addWidget(self.autoBrushBox, 0, 1)
        optionsLayout.addWidget(self.syncBox, 1, 1)
        optionsLayout.setVerticalSpacing(16)
        self.mainLayout.addLayout(optionsLayout)

    def openConfig(self):
        self.saveKit(self.currentIndex, self.currentText)
        config = SyncConfig(self)
        config.exec()

    def setPrevText(self):
        self.prevText = self.currentText
        self.currentText = self.kitBox.currentText()
    
    def selectKit(self):
        if self.currentIndex == -2:
            return
        
        self.prevIndex = self.currentIndex
        self.currentIndex = self.kitBox.currentIndex()
        if self.prevIndex != -1:
            self.saveKit(self.prevIndex, self.prevText)
        
        self.slot.clear()
        if self.currentText in self.ten.kits:
            allPresets = Application.resources('preset')
            kit = self.ten.kits[self.currentText]
            for index, slot in enumerate(kit):
                self.loadModel(allPresets, index, slot)

    def getUniqueName(self, name: str):
        copy = i18n("Copy")
        while self.kitBox.findText(name) != -1:
            name += f"({copy})"
        return name
    
    def newKit(self):
        self.saveKit(self.currentIndex, self.currentText)
        self.currentIndex = -1

        name = self.getUniqueName(i18n("New"))
        self.kitBox.addItem(name)
        
        index = self.kitBox.findText(name)
        self.kitBox.setCurrentIndex(index)

    def moveKit(self):
        length = self.kitBox.count()
        if length > 1:
            self.saveKit(self.currentIndex, self.currentText)
            kit = self.kitBox.itemText(self.currentIndex)

            if self.kitBox.sender().toolTip() == i18n("Move Down Selected Kit") and self.currentIndex < length - 1:
                destination = self.currentIndex + 1
            elif self.kitBox.sender().toolTip() == i18n("Move Up Selected Kit") and self.currentIndex > 0:
                destination = self.currentIndex - 1
            else:
                return
            
            self.currentIndex = -2
            self.kitBox.removeItem(self.kitBox.currentIndex())
            self.kitBox.insertItem(destination, kit)
            self.kitBox.setCurrentIndex(destination)
            self.currentIndex = destination

    def deleteKit(self):
        confirmDelete = QMessageBox().warning(self, i18n("Confirm Deletion"), 
                                              i18n("This operation cannot be undone.\n\nProceed with deleting kit?"), 
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirmDelete == QMessageBox.StandardButton.Yes:
            kit = self.kitBox.itemText(self.currentIndex)
            self.ten.removeKit(kit)
            if self.ten.sync.isKitStored(kit):
                self.ten.sync.removeKit(kit)
            
            if self.kitBox.count() > 1:
                self.currentIndex = -1
                self.kitBox.removeItem(self.kitBox.currentIndex())
            else:
                self.kitBox.setItemText(0, "")
                self.slot.clear()

    def insertPreset(self):
        index = self.slot.addButtons.index(self.sender())
        choosePreset = ChoiceDialog(self)
        if choosePreset.exec():
            preset = self.chosenPreset

            if preset.name() in self.slot.presets:
                prevIndex = self.slot.presets[preset.name()]
                shortcut = self.slot.shortcuts[prevIndex]
                movePreset = QMessageBox().question(self, i18n("Preset Chooser"), 
                                                    i18n(f"Preset already in slot {shortcut}.\n\nMove it instead?"))
                
                if movePreset == QMessageBox.StandardButton.No:
                    return
                elif movePreset == QMessageBox.StandardButton.Yes:
                    remove = -1
                    prevModel = self.slot.models[prevIndex]
                    
                    for row in range(prevModel.rowCount()):
                        item =  prevModel.item(row)
                        if item.toolTip() == preset.name() and item.statusTip() != DividerItem.Name:
                            remove = row
                            break
                    
                    if remove >= 0:
                        prevModel.removeRow(remove)

            self.slot.presets[preset.name()] = index
            view = self.slot.views[index]
            model =  self.slot.models[index]
            selectedIndexes = view.selectedIndexes()
            view.clearSelection()

            if selectedIndexes == []:
                view.scrollTo(self.insertItem(model, view, model.rowCount(), preset))
                return
            
            selectedIndexes.sort(key=lambda x: model.itemFromIndex(x).row())
            row = model.itemFromIndex(selectedIndexes[0]).row() + 1
            view.scrollTo(self.insertItem(model, view, row, preset))

    def insertItem(self, model: QStandardItemModel, view: QListView, row: int, preset=None):
        if preset != None:
            item = PresetItem(QIcon(QPixmap.fromImage(preset.image())), preset.name())
        else:
            item = DividerItem()
        
        model.insertRow(row, item)
        modelIndex = model.indexFromItem(item)
        view.selectionModel().select(modelIndex, QItemSelectionModel.SelectionFlag.Select)
        return modelIndex

    def insertDividers(self):
        index = self.slot.grpButtons.index(self.sender())
        model = self.slot.models[index]
        view = self.slot.views[index]
        selectedIndexes = view.selectedIndexes()
        view.clearSelection()
        
        if not selectedIndexes:
            view.scrollTo(self.insertItem(model, view, model.rowCount()))
            return
        
        rows = []
        for modelIndex in selectedIndexes:
            rows.append(model.itemFromIndex(modelIndex).row())
        
        for endStart in self.getReversedRanges(rows):
            end = endStart[0]
            start = endStart[1]
            
            if model.item(end).statusTip() != DividerItem.Name:
                if end < model.rowCount() - 1:
                    if model.item(end + 1).statusTip() != DividerItem.Name:
                        self.insertItem(model, view, end + 1)
            
            if model.item(start).statusTip() != DividerItem.Name:
                if start > 0:
                    if model.item(start - 1).statusTip() != DividerItem.Name:
                        self.insertItem(model, view, start)
        
        newIndexes = sorted(view.selectedIndexes(), key=lambda x : model.itemFromIndex(x).row())
        if newIndexes:
            view.scrollTo(newIndexes[0])

    def getReversedRanges(self, rows: List[int]):
        rows.sort(reverse=True)
        first = last = rows[0]
        for n in rows[1:]:
            if n + 1 == last:
                last = n
            else:
                yield first, last
                first = last = n
        yield first, last

    def removeItems(self):
        index = self.slot.delButtons.index(self.sender())
        model = self.slot.models[index]
        view = self.slot.views[index]
        
        rows = []
        for modelIndex in view.selectedIndexes():
            rows.append(model.itemFromIndex(modelIndex).row())
        
        for row in sorted(rows, reverse=True):
            model.removeRow(row)

    def editedSlots(self, kit: str):
        slots = []
        for index in range(len(self.slot.models)):
            model = self.slot.models[index]
            
            slot = []
            group = []
            for row in range(model.rowCount()):
                item = model.item(row)
                if item.statusTip() == DividerItem.Name:
                    if group:
                        slot.append(group)
                        group = []
                else:
                    group.append(item.toolTip())
            if group:
                slot.append(group)
            slots.append(slot)

        if kit not in self.ten.kits:
            return slots
        
        if slots != self.ten.kits[kit]:
            return slots
    
    def saveKit(self, index: int, text: str):
        kit = self.kitBox.itemText(index)
        text = text.replace(",", " ")
        stored = self.ten.sync.isKitStored(kit)

        if kit != text:
            name = self.getUniqueName(text)
            self.kitBox.setItemText(index, name)
            if kit in self.ten.kits:
                self.ten.updateName(kit, name)
            if stored:
                self.ten.sync.renameKit(kit, name)
            kit = name
        
        slots = self.editedSlots(kit)
        if slots:
            self.ten.updateKit(kit, slots)
            if not stored:
                self.ten.sync.newKit(kit)

    def closeEvent(self, event):
        self.saveKit(self.currentIndex, self.currentText)
        
        kitOrder = []
        for index in range(self.kitBox.count()):
            kitOrder.append(self.kitBox.itemText(index))
        if kitOrder != list(self.ten.kits.keys()):
            self.ten.reorderKits(kitOrder)
        
        if self.ten.activatePrev != self.activatePrevBox.isChecked():
            self.ten.activatePrev = self.activatePrevBox.isChecked()
            self.ten.updateSettings = True

        if self.ten.activateNext != self.activateNextBox.isChecked():
            self.ten.activateNext = self.activateNextBox.isChecked()
            self.ten.updateSettings = True

        if self.ten.nextGroup != self.nextGroupButton.isChecked():
            self.ten.nextGroup = self.nextGroupButton.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.autoBrush != self.autoBrushBox.isChecked():
            self.ten.autoBrush = self.autoBrushBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.active != self.syncBox.isChecked():
            self.ten.sync.active = self.syncBox.isChecked()
            self.ten.updateSettings = True

        if self.currentText != self.ten.activeKit[self.windex] or self.currentText in self.ten.kitsEdited:
            self.ten.setActiveKit(self.currentText, self.windex)

        event.accept()

