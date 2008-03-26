import canvas
import copy

class History() :

    def __init__(self, canvas) :
        self.canvas = canvas
        self.undo_stack = []
        self.redo_stack = []
        self.change_popup_status()

    def push_undo(self, id) :
        "Pushes into the undo_stack all the elements present in the canvas."

        dump = [(box.x, box.y, box.model) for box in self.canvas.boxes]
        self.undo_stack.append((id, copy.deepcopy(dump)))
        self.change_popup_status()

    def pop_undo(self) :
        "Pops one element from the undo_stack, creates all the boxes y pushes it again in the redo_stack"

        dump = self.undo_stack.pop()
        id = dump [0]
        list = dump [1]
        self.redo_stack.append((id, list))

        if id == 'BOX_CREATED' :
            if self.undo_stack == [] :
                self.canvas._clear()

            else :
                self.canvas._clear()
                last_element = self.undo_stack [len (self.undo_stack) - 1]
                id = last_element [0]
                list_boxes = last_element [1]

                for box in list_boxes :
                    self.canvas.create_box(box [2], box [0], box [1])

        self.change_popup_status()

    def pop_redo(self) :
        "Pops one element from the redo_stack, creates all the boxes y pushes it again in the undo_stack"

        dump = self.redo_stack.pop()
        id = dump [0]
        list_boxes = dump [1]
        self.undo_stack.append((id, list_boxes))

        if id == 'BOX_CREATED' :
            self.canvas._clear()
            for box in list_boxes :
                self.canvas.create_box(box [2], box [0], box [1])
                
        self.change_popup_status()

    def change_popup_status(self) :
        "Checks both stacks to see if any of them are empty. In that case we disable the undo and/or redo actions."

        if self.undo_stack == [] :
            self.canvas.popup.view.undo.set_sensitive(False)
        else :
            self.canvas.popup.view.undo.set_sensitive(True)

        if self.redo_stack == [] :
            self.canvas.popup.view.redo.set_sensitive(False)
        else :
            self.canvas.popup.view.redo.set_sensitive(True)

