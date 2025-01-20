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
                             QGroupBox, QGridLayout, QComboBox)
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
        self.presetChooser.presetClicked.connect(self.accept)
        self.mainLayout.addWidget(self.presetChooser)

    def accept(self):
        self.editor.chosenPreset = self.presetChooser.currentPreset()
        super().accept()


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
        self.kitList = QComboBox()
        self.kitList.addItems(self.ten.kits.keys())
        self.kitList.setEditable(True)
        self.kitList.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.kitList.setMinimumWidth(240)
        self.kitList.setCurrentIndex(self.kitList.findText(self.ten.activeKit[self.windex]))
        self.currentText = self.kitList.currentText()
        self.prevText = self.currentText
        self.kitList.editTextChanged.connect(self.setPrevText)
        self.currentIndex = self.kitList.currentIndex()
        self.prevIndex = self.currentIndex
        self.kitList.currentIndexChanged.connect(self.selectKit)

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
        kitsLayout.addWidget(self.kitList)
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
        self.activatePrevBox = QGroupBox(i18n("S&witch to Previous Brush on 2nd Press"))
        self.activatePrevBox.setCheckable(True)
        self.activatePrevBox.setChecked(self.ten.activatePrev)
        self.activatePrevBox.setToolTip(i18n("Only Switches if Slot Does Not Have Groups"))
        self.enforcePrevBox = QCheckBox(i18n("&Enforce Switching to Previous Brush"))
        self.enforcePrevBox.setToolTip(i18n("Ignores Switch to Next Group on 2nd Press"))
        self.enforcePrevBox.setChecked(self.ten.enforcePrev)

        prevBoxLayout = QVBoxLayout()
        prevBoxLayout.addWidget(self.enforcePrevBox)
        self.activatePrevBox.setLayout(prevBoxLayout)
        panelLayout = QVBoxLayout()
        panelLayout.addWidget(self.activatePrevBox)
        
        self.autoBrushBox = QCheckBox(i18n("&Auto-Select Freehand Brush Tool"))
        self.autoBrushBox.setToolTip(i18n("Also Prevents 2nd Press Actions if Tool Not Selected"))
        self.autoBrushBox.setChecked(self.ten.autoBrush)
        panelLayout.addSpacing(4)
        panelLayout.addWidget(self.autoBrushBox)
        
        self.syncBox = QGroupBox(i18n("&Sync Settings When Switching Group/Position"))
        self.syncBox.setCheckable(True)
        self.syncBox.setChecked(self.ten.sync.active)
        self.sizeBox = QCheckBox(i18n("Brush Si&ze"))
        self.sizeBox.setChecked(self.ten.sync.size)
        self.opacityBox = QCheckBox(i18n("Painting Opa&city"))
        self.opacityBox.setChecked(self.ten.sync.opacity)
        self.flowBox = QCheckBox(i18n("Painting &Flow"))
        self.flowBox.setChecked(self.ten.sync.flow)
        self.eraseBox = QCheckBox(i18n("E&rase Mode"))
        self.eraseBox.setChecked(self.ten.sync.erase)

        syncBoxLayout = QGridLayout()
        syncBoxLayout.addWidget(self.sizeBox, 0 ,0)
        syncBoxLayout.addWidget(self.opacityBox, 0 ,1)
        syncBoxLayout.addWidget(self.flowBox, 1 ,1)
        syncBoxLayout.addWidget(self.eraseBox, 1 ,0)
        self.syncBox.setLayout(syncBoxLayout)

        optionsLayout = QHBoxLayout()
        optionsLayout.addLayout(panelLayout)
        optionsLayout.addWidget(self.syncBox)
        self.mainLayout.addLayout(optionsLayout)

    def setPrevText(self):
        self.prevText = self.currentText
        self.currentText = self.kitList.currentText()
    
    def selectKit(self):
        if self.currentIndex == -2:
            return
        
        self.prevIndex = self.currentIndex
        self.currentIndex = self.kitList.currentIndex()
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
        while self.kitList.findText(name) != -1:
            name += f"({copy})"
        return name
    
    def newKit(self):
        self.saveKit(self.currentIndex, self.currentText)
        self.currentIndex = -1

        name = self.getUniqueName(i18n("New"))
        self.kitList.addItem(name)
        
        index = self.kitList.findText(name)
        self.kitList.setCurrentIndex(index)

    def moveKit(self):
        length = self.kitList.count()
        if length > 1:
            self.saveKit(self.currentIndex, self.currentText)
            kit = self.kitList.itemText(self.currentIndex)

            if self.kitList.sender().toolTip() == i18n("Move Down Selected Kit") and self.currentIndex < length - 1:
                destination = self.currentIndex + 1
            elif self.kitList.sender().toolTip() == i18n("Move Up Selected Kit") and self.currentIndex > 0:
                destination = self.currentIndex - 1
            else:
                return
            
            self.currentIndex = -2
            self.kitList.removeItem(self.kitList.currentIndex())
            self.kitList.insertItem(destination, kit)
            self.kitList.setCurrentIndex(destination)
            self.currentIndex = destination

    def deleteKit(self):
        confirmDelete = QMessageBox().warning(self, i18n("Confirm Deletion"), 
                                              i18n("This operation cannot be undone.\n\nProceed with deleting kit?"), 
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirmDelete == QMessageBox.StandardButton.Yes:
            kit = self.kitList.itemText(self.currentIndex)
            self.ten.removeKit(kit)
            
            if self.kitList.count() > 1:
                self.currentIndex = -1
                self.kitList.removeItem(self.kitList.currentIndex())
            else:
                self.kitList.setItemText(0, "")
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
                                                    i18n(f"Preset already in slot {shortcut}.\n\nMove it instead?"), 
                                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
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
        kit = self.kitList.itemText(index)

        if kit != text:
            name = self.getUniqueName(text)
            self.kitList.setItemText(index, name)
            if kit in self.ten.kits:
                self.ten.updateName(kit, name)
            kit = name

        slots = self.editedSlots(kit)
        if slots:
            self.ten.updateKit(kit ,slots)

    def saveOptions(self):
        if self.ten.activatePrev != self.activatePrevBox.isChecked():
            self.ten.activatePrev = self.activatePrevBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.enforcePrev != self.enforcePrevBox.isChecked():
            self.ten.enforcePrev = self.enforcePrevBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.autoBrush != self.autoBrushBox.isChecked():
            self.ten.autoBrush = self.autoBrushBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.active != self.syncBox.isChecked():
            self.ten.sync.active = self.syncBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.size != self.sizeBox.isChecked():
            self.ten.sync.size = self.sizeBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.opacity != self.opacityBox.isChecked():
            self.ten.sync.opacity = self.opacityBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.flow != self.flowBox.isChecked():
            self.ten.sync.flow = self.flowBox.isChecked()
            self.ten.updateSettings = True
        
        if self.ten.sync.erase != self.eraseBox.isChecked():
            self.ten.sync.erase = self.eraseBox.isChecked()
            self.ten.updateSettings = True

    def closeEvent(self, event):
        self.saveKit(self.currentIndex, self.currentText)
        self.currentText = self.kitList.itemText(self.currentIndex)
        
        kitOrder = []
        for index in range(self.kitList.count()):
            kitOrder.append(self.kitList.itemText(index))
        if kitOrder != list(self.ten.kits.keys()):
            self.ten.reorderKits(kitOrder)
        
        self.saveOptions()

        if self.currentText != self.ten.activeKit[self.windex] or self.currentText in self.ten.kitsEdited:
            self.ten.setActiveKit(self.currentText, self.windex)

        event.accept()

