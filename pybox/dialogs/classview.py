    # -*- encoding: utf-8 -*-
import gtk
import gtk.glade

from window import Window

NONE_CLASS = "<None>"

class ClassView(Window):
    """Representa las propiedades de una clase de forma visual.

    Se utiliza en dos casos, cuando se quiere crear un nuevo objeto
    y cuando se modifican los datos de una clase existente."""

    def __init__(self, model, classes):
        Window.__init__(self, 'class.glade')
        self.view.accept.set_sensitive(False)
        self.view.addattr.set_sensitive(False)
        self.view.addmethod.set_sensitive(False)
        self.model = model
        self.view.name.set_text(model.name)
        #self.view.superclass.set_active(model.superclass)
        self.view.abstract.set_active(model.abstract)

        # Permite realizar multiples selecciones sobre el treeview (con shift y ctrl)
        # Allows us to make multiple selections on the treeview.

        treeselection_mode = self.view.treeview_attributes.get_selection()
        treeselection_mode.set_mode(gtk.SELECTION_MULTIPLE)

        treeselection_mode = self.view.treeview_methods.get_selection()
        treeselection_mode.set_mode(gtk.SELECTION_MULTIPLE)

        self._create_superclass_list(classes)

        if model.superclass:
            list = [n[0] for n in self.view.superclass.get_model()]
            try:
                #TODO
                #Agrego el [0] para hacer pruebas para la herencia multiple
                self.view.superclass.set_active(list.index(model.superclass[0]))
            except:
                print "Ups!, la superclase de este modelo se ha borrado."

        self.load_attributes()

    def _create_superclass_list(self, classes):
        store = gtk.ListStore(str)

        store.append([NONE_CLASS])

        for name in classes:
            if name != self.model.name:
                store.append([name])

        combo = self.view.superclass
        combo.set_model(store)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.set_active(0)

        # Solo permite elegir superclase en caso de tener disponibilidad.
        if len(store) > 1:
            combo.set_sensitive(True)
        else:
            combo.set_sensitive(False)

    def load_attributes(self):
        # Armamos el treeview de los atributos.
        # We build the attribute treeview

        attribute_column = gtk.TreeViewColumn('Atributtes', gtk.CellRendererText(), 
                text=0)
        self.view.treeview_attributes.append_column(attribute_column)
        attribute_model = gtk.ListStore(str)

        for item in self.model.variables:
            attribute_model.append([item])

        self.view.treeview_attributes.set_model(attribute_model)

        # Armamos el treeview de los metodos.
        # We build the method treeview.

        method_column = gtk.TreeViewColumn('Methods', gtk.CellRendererText(), 
                text=0)
        self.view.treeview_methods.append_column(method_column)
        method_model= gtk.ListStore(str)
        
        for item in self.model.methods:
            method_model.append([item])

        self.view.treeview_methods.set_model(method_model)

    def on_dialog1__delete_event(self, widget, extra):
        self.view.dialog1.response(0)
        self.view.dialog1.destroy()
    
    def on_name__changed(self, widget):
        # Si se escribe el nombre de la clase entonces permitimos que el usuario pueda presionar OK para crearla.
        # If the name of the class is written then we allow the user to create the class.

        if len(self.view.name.get_text()) > 0:
            self.view.accept.set_sensitive(True)
        else:
            self.view.accept.set_sensitive(False)

    def on_attrentry__changed(self, widget):
        if len(self.view.attrentry.get_text()) > 0:
            self.view.addattr.set_sensitive(True)
        else:
            self.view.addattr.set_sensitive(False)

        # validacion
        text = self.view.attrentry.get_text() 
        #print "text:", text
        #print "lista:", self.model.variables
        
        model_attributes = self.view.treeview_attributes.get_model()
        variables = [name[0] for name in model_attributes]

        if text in variables:
            import gtk
            import gtk.gdk
            self.view.error.show()
            self.view.attrentry.modify_base(gtk.STATE_NORMAL,
                gtk.gdk.color_parse('#FFDDDD'))
        else:
            import gtk
            import gtk.gdk
            self.view.error.hide()
            self.view.attrentry.modify_base(gtk.STATE_NORMAL,
                gtk.gdk.color_parse('#FFFFFF'))

    def on_methodentry__changed(self, widget):
        if len(self.view.methodentry.get_text()) > 0:
            self.view.addmethod.set_sensitive(True)
        else:
            self.view.addmethod.set_sensitive(False)

    def on_attrentry__activate(self, widget):
        if len(self.view.attrentry.get_text()) > 0:
            self.on_addattr__clicked(widget)

    def on_methodentry__activate(self, widget):
        if len(self.view.methodentry.get_text()) > 0:
            self.on_addmethod__clicked(widget)

    def on_accept__clicked(self, widget):
        #print "Nombre anterior:", self.model.name
        self.model.name = self.view.name.get_text()
        #print "Nombre nuevo:", self.model.name
        
        #TODO
        ''' para probar a superclasss como lista hago que el único string
        seleccionado pase a ser una lista de un elemento'''
        superclass = [self.view.superclass.get_active_text()]

        if superclass and superclass != [NONE_CLASS]:
            self.model.superclass = superclass
        else:
            self.model.superclass = []

        self.model.abstract = self.view.abstract.get_active()

        model_attributes = self.view.treeview_attributes.get_model()
        self.model.variables = [name[0] for name in model_attributes]

        model_methods = self.view.treeview_methods.get_model()
        self.model.methods = [name[0] for name in model_methods]
        
        # Al presionar OK, cerramos la ventana.
        # When we press OK we close the window.
        self.view.dialog1.destroy()

    def on_cancel__clicked(self, widget):
        self.view.dialog1.destroy()

    def on_removeattr__clicked(self, widget):
        treeview_selection = self.view.treeview_attributes.get_selection()
        model, selected_rows = treeview_selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected_rows]

        for iter in iters:
            model.remove(iter)

    def on_removemethod__clicked(self, widget):
        treeview_selection = self.view.treeview_methods.get_selection()
        model, selected_rows = treeview_selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected_rows]

        for iter in iters:
            model.remove(iter)

    def on_addattr__clicked(self, widget):
        model = self.view.treeview_attributes.get_model()
        model.append([self.view.attrentry.get_text()])
        self.view.treeview_attributes.set_model(model)
        self.view.attrentry.set_text('')

    def on_addmethod__clicked(self, widget):
        model = self.view.treeview_methods.get_model()
        model.append([self.view.methodentry.get_text()])
        self.view.treeview_methods.set_model(model)
        self.view.methodentry.set_text('')
