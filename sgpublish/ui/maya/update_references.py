import functools
import itertools
import os

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from sgfs import SGFS

from .. import utils as ui_utils


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
        self._populate_references()
    
    def _setup_ui(self):
        
        self.setWindowTitle("Update References")
        self.setMinimumWidth(1000)
        self.setLayout(QtGui.QVBoxLayout())
        
        self._tree = QtGui.QTreeWidget()
        self._tree.setIndentation(0)
        self._tree.setItemsExpandable(False)
        self._tree.setHeaderLabels(["Namespace", "Entity", "Step", "Task", "Type", "Name", "Version"])
        self.layout().addWidget(self._tree)
        
        
        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch()
        
        self._update_button = QtGui.QPushButton('Update All')
        button_layout.addWidget(self._update_button)
        
        self._close_button = QtGui.QPushButton('Close')
        button_layout.addWidget(self._close_button)
        
    
    def _populate_references(self):
        
        sgfs = SGFS()
        
        for path in cmds.file(q=True, reference=True):
            
            publishes = sgfs.entities_from_path(path)
            if not publishes or publishes[0]['type'] != 'PublishEvent':
                print '# Skipping', path
            publish = publishes[0]
            
            # Some do not have all of these.
            publish.fetch(('sg_link', 'code', 'sg_type', 'sg_version'))
            
            siblings = sgfs.session.find('PublishEvent', [
                ('sg_link', 'is', publish['sg_link']),
                ('code', 'is', publish['code']),
                ('sg_type', 'is', publish['sg_type']),
            ], ['sg_path'])
            siblings.sort(key=lambda x: x['sg_version'])
            max_version = max(x['sg_version'] for x in siblings)
            
            task = publish.parent()
            entity = task.parent()
            namespace = cmds.file(path, q=True, namespace=True)
            node = cmds.referenceQuery(path, referenceNode=True)
            item = QtGui.QTreeWidgetItem([
                namespace,
                entity['code'],
                task.fetch('step.Step.code'),
                task['content'],
                publish['sg_type'],
                publish['code'],
                'v%04d' % publish['sg_version']
            ])
            item.setIcon(0, ui_utils.icon('silk/tick' if publish['sg_version'] == max_version else 'silk/cross', size=12, as_icon=True))
            item.setData(0, Qt.UserRole, {'publish': publish, 'siblings': siblings})
            
            combo = QtGui.QComboBox()
            for i, sibling in enumerate(siblings):
                combo.addItem('v%04d' % sibling['sg_version'], sibling)
                if sibling['sg_version'] == publish['sg_version']:
                    combo.setCurrentIndex(i)
            combo.currentIndexChanged.connect(functools.partial(self._combo_changed, node, siblings))
            self._tree.addTopLevelItem(item)
            self._tree.setItemWidget(item, 6, combo)
        
        for i in range(7):
            self._tree.resizeColumnToContents(i)
            self._tree.setColumnWidth(i, self._tree.columnWidth(i) + 10)
    
    def _combo_changed(self, node, publishes, index):
        publish = publishes[index]
        path = publish['sg_path']
        print '#', node, 'to', path
        cmds.file(
            path,
            loadReference=node,
            type='mayaAscii' if path.endswith('.ma') else 'mayaBinary',
            options='v=0',
        )
        #publish.fetch('sg_path'), namespace=namespace, reference=True)


def __before_reload__():
    if dialog:
        dialog.close()


dialog = None


def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = Dialog()    
    dialog.show()
    dialog.raise_()
    
