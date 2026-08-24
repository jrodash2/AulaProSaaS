from django import forms


class AulaProFormMixin:
    """Aplica la identidad visual de AulaPro sin destruir atributos existentes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()

    def aplicar_estilos(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"
            classes = widget.attrs.get("class", "").split()
            if css_class not in classes:
                classes.append(css_class)
            if self.is_bound and name in self.errors and "is-invalid" not in classes:
                classes.append("is-invalid")
            widget.attrs["class"] = " ".join(classes)
