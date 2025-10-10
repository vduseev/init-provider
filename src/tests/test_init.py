import pytest

from init_provider import BaseProvider, requires
from init_provider.exceptions import (
    CircularDependency,
    InitError,
    SelfDependency,
    AttributeNotInitialized,
)


def test_access_before_initialize(clean_sys_modules):
    class Provider(BaseProvider):
        _init_counter = 0

        def provider_init(self):
            self._init_counter += 1

    assert Provider.__provider_initialized__ is False
    assert Provider._init_counter == 0


def test_assign_before_initialize(clean_sys_modules):
    class Provider(BaseProvider):
        data: str
        _init_counter = 0

        def provider_init(self):
            self.data = "data"
            self._init_counter += 1

    assert Provider._init_counter == 0
    assert "data" in Provider.__provider_guarded_attrs__

    Provider.data = "other"
    assert "data" not in Provider.__provider_guarded_attrs__
    assert Provider._init_counter == 0
    assert Provider.data == "other"
    assert Provider.__provider_guarded_attrs__ == set()
    assert Provider.__provider_initialized__ is False
    assert Provider._init_counter == 0


def test_dependency_order(clean_sys_modules):
    order = []

    class ProviderA(BaseProvider):
        a: str
        _init_counter = 0

        def provider_init(self):
            self.a = "A"
            self._init_counter += 1
            order.append("A")

        def get_a(self) -> str:
            return self.a

    @requires(ProviderA)
    class ProviderB(BaseProvider):
        """Docstring of provider B"""

        b: str
        """Docstring of guarded attribute B"""
        _init_counter = 0
        """init counter of provider B"""

        def provider_init(self):
            self.b = "B"
            self._init_counter += 1
            order.append("B")

    @requires(ProviderA, ProviderB)
    class ProviderC(BaseProvider):
        c: str = "C"
        """Docstring of initialized attribute C"""
        _init_counter = 0
        """init counter of provider C"""

        def provider_init(self):
            self._init_counter += 1
            order.append("C")

        def get_abc(self) -> str:
            """Docstring of get_abc method"""
            return f"{ProviderA.a}{ProviderB.b}{self.c}"

    # Accessing A first, doesn't trigger initialization in B or C
    assert ProviderA.a == "A"
    assert ProviderA.get_a() == "A"
    assert ProviderA._init_counter == 1
    assert ProviderB._init_counter == 0
    assert ProviderC._init_counter == 0
    assert order == ["A"]

    # Accessing C triggers initialization in A, B, and C
    assert ProviderC.get_abc() == "ABC"
    assert order == ["A", "B", "C"]
    assert ProviderA._init_counter == 1
    assert ProviderB._init_counter == 1
    assert ProviderC._init_counter == 1

    # Accessing B triggers nothing, because everything is already initialized
    assert ProviderB.b == "B"
    assert ProviderA._init_counter == 1
    assert ProviderB._init_counter == 1
    assert ProviderC._init_counter == 1
    assert order == ["A", "B", "C"]


def test_circular_dependency_detection(clean_sys_modules):
    """craft two providers with mutual @requires; importing class raises CircularDependency."""

    class CircularA(BaseProvider):
        def provider_init(self):
            pass

        def get_a(self) -> str:
            return "a"

    @requires(CircularA)
    class CircularB(BaseProvider):
        def provider_init(self):
            pass

        def get_b(self) -> str:
            return "b"

    # Now create the circular dependency by making A depend on B
    CircularA.__provider_dependencies__ = {CircularB}

    # Accessing either should detect the circular dependency
    with pytest.raises(CircularDependency):
        CircularA.get_a()

    with pytest.raises(CircularDependency):
        CircularB.get_b()


def test_self_dependency_detection(clean_sys_modules):
    class SelfDependentProvider(BaseProvider):
        _init_counter = 0
        value: int

        def provider_init(self):
            self.value = self.compute_value()
            self._init_counter += 1

        def compute_value(self) -> int:
            return self._init_counter

    with pytest.raises(SelfDependency):
        SelfDependentProvider.value

    assert SelfDependentProvider._init_counter == 0


def test_initialize_raise_exception(clean_sys_modules):
    class FailingProvider(BaseProvider):
        _init_counter = 0

        def provider_init(self):
            self._init_counter += 1
            raise ValueError("Database connection failed")

        def get_counter(self):
            return self._init_counter

    with pytest.raises(InitError):
        FailingProvider.get_counter()


def test_attribute_unset_error(clean_sys_modules):
    class BadProvider(BaseProvider):
        unset_attribute: str

        def provider_init(self):
            pass

    with pytest.raises(AttributeNotInitialized):
        BadProvider.unset_attribute
