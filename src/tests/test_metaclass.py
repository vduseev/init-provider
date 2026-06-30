import inspect

from init_provider import BaseProvider, init
from init_provider.provider import ProviderMetaclass


def test_basic(clean_sys_modules):
    class TestProvider(BaseProvider):
        guarded_attr: str
        _init_counter = 0

        def __init__(self):
            self.guarded_attr = "A"
            self._init_counter += 1

        @init
        def get_guarded_attr(self) -> str:
            return self.guarded_attr

    # Metaclass
    assert TestProvider.__class__ is ProviderMetaclass
    assert TestProvider.__bases__ == (BaseProvider,)
    assert TestProvider.__provider_created__ is False
    assert TestProvider.__provider_dependencies__ == set()
    assert TestProvider.__provider_init__ is not None  # type: ignore[unresolved-attribute]

    # Guards
    assert not inspect.isfunction(TestProvider.get_guarded_attr)
    assert inspect.ismethod(TestProvider.get_guarded_attr)
    assert "guarded_attr" in TestProvider.__provider_guarded_attrs__
    assert "_init_counter" not in TestProvider.__provider_guarded_attrs__


def test_guarded_attrs_from_lazy_annotations(clean_sys_modules):
    """Guarded attributes are derived from class annotations even when those
    annotations are evaluated lazily (PEP 649, default on Python 3.14+) and
    reference names that are not defined at class-creation time.

    On 3.14 the class namespace carries an ``__annotate_func__`` instead of a
    populated ``__annotations__``; the metaclass recovers the annotated names
    via ``annotationlib.call_annotate_function`` in FORWARDREF format, which
    tolerates the undefined forward reference below.
    """

    class FwdProvider(BaseProvider):
        plain: str
        forward: "UndefinedAtClassCreation"  # noqa: F821 - never evaluated
        with_default: int = 5

        def __init__(self):
            self.plain = "x"
            self.forward = object()

    assert "plain" in FwdProvider.__provider_guarded_attrs__
    assert "forward" in FwdProvider.__provider_guarded_attrs__
    # Annotated-with-a-value attributes are not guarded.
    assert "with_default" not in FwdProvider.__provider_guarded_attrs__
