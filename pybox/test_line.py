# -*- encoding: utf-8 -*
import gtk
import main
import model

if __name__ == '__main__':
    main = main.Main()

    # Modelo de clases generado
    #
    #   Mascota    Canino
    #      ^        ^
    #       \      /
    #        \    /
    #         Perro
    #           ^
    #           |
    #           |
    #        Caniche
    #
    mascota = model.Model("Mascota", [], True, "", ['nombre', 'edad'], [])
    canino = model.Model("Canino", [], True, "", [], [])
    perro = model.Model("Perro", ["Mascota", "Canino"], False, "", [], [])
    caniche = model.Model("Caniche", ["Perro"], False, "", ['dueño'], [])

    main.canvas.create_box(mascota, 50, 20)
    main.canvas.create_box(canino, 280, 20)
    main.canvas.create_box(perro, 180, 100)
    main.canvas.create_box(caniche, 300, 120)

    gtk.main()
