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
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"
            classes = widget.attrs.get("class", "").split()
            if css_class not in classes:
                classes.append(css_class)
            # Never access ``self.errors`` while a subclass is still running
            # ``__init__``: doing so triggers validation before it can finish
            # configuring tenant-aware/dynamic choices.
            if self._errors is not None and name in self._errors and "is-invalid" not in classes:
                classes.append("is-invalid")
            widget.attrs["class"] = " ".join(classes)

    def full_clean(self):
        super().full_clean()
        # Validation has finished, so error classes can now be applied safely.
        self.aplicar_estilos()
