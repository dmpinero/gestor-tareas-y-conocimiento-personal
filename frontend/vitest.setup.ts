// jsdom no implementa scrollIntoView; Reka UI lo llama al resaltar la
// opción elegida en un Combobox (incluso al fijar el valor por proxy, sin
// abrir el desplegable), lo que rompe cualquier test que monte uno.
Element.prototype.scrollIntoView = () => {}
