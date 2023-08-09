class PseudoList(list):
    """
    `list` subclass that doesn't implement any of the methods.

    Meant for cases in which an external library requires that something be a
    subclass of `list`, but the actually used (effective) interface is much
    smaller. In such a case, you can derive from this class and only implement
    the effective interface, while all unused methods raise exceptions when
    called, ensuring obvious errors instead of hard to find bugs.
    """

    EXC_MESSAGE: str = "see PseudoList docstring"

    def not_impl(self):
        raise NotImplementedError(self.EXC_MESSAGE)

    def __add__(self, *args, **kwargs):
        self.not_impl()

    def __contains__(self, *args, **kwargs):
        self.not_impl()

    def __delitem__(self, *args, **kwargs):
        self.not_impl()

    def __eq__(self, *args, **kwargs):
        self.not_impl()

    def __ge__(self, *args, **kwargs):
        self.not_impl()

    def __getitem__(self, *args, **kwargs):
        self.not_impl()

    def __gt__(self, *args, **kwargs):
        self.not_impl()

    def __iadd__(self, *args, **kwargs):
        self.not_impl()

    def __imul__(self, *args, **kwargs):
        self.not_impl()

    def __iter__(self, *args, **kwargs):
        self.not_impl()

    def __le__(self, *args, **kwargs):
        self.not_impl()

    def __len__(self, *args, **kwargs):
        self.not_impl()

    def __lt__(self, *args, **kwargs):
        self.not_impl()

    def __mul__(self, *args, **kwargs):
        self.not_impl()

    def __ne__(self, *args, **kwargs):
        self.not_impl()

    def __repr__(self, *args, **kwargs):
        self.not_impl()

    def __reversed__(self, *args, **kwargs):
        self.not_impl()

    def __rmul__(self, *args, **kwargs):
        self.not_impl()

    def __setitem__(self, *args, **kwargs):
        self.not_impl()

    def __sizeof__(self, *args, **kwargs):
        self.not_impl()

    def append(self, *args, **kwargs):
        self.not_impl()

    def clear(self, *args, **kwargs):
        self.not_impl()

    def copy(self, *args, **kwargs):
        self.not_impl()

    def count(self, *args, **kwargs):
        self.not_impl()

    def extend(self, *args, **kwargs):
        self.not_impl()

    def index(self, *args, **kwargs):
        self.not_impl()

    def insert(self, *args, **kwargs):
        self.not_impl()

    def pop(self, *args, **kwargs):
        self.not_impl()

    def remove(self, *args, **kwargs):
        self.not_impl()

    def reverse(self, *args, **kwargs):
        self.not_impl()

    def sort(self, *args, **kwargs):
        self.not_impl()
