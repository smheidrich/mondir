from collections.abc import Callable, Mapping
from os import PathLike
from pathlib import Path
from typing import Any, cast

from jinja2 import BaseLoader, Environment, FileSystemLoader

from .jinja2.extension import ExtendedEnvironment, MondirData, extensions
from .utils.path import mkdir_parents_up_to


class TemplateLoadingError(Exception):
    """
    Raised when a particular template file could not be loaded.
    """


class TemplateRenderingError(Exception):
    """
    Raised when a particular template could not be rendered.
    """


class TemplateOutputError(Exception):
    """
    Raised when a rendered template could not be written to disk.
    """


class DirTemplate:
    """
    A template encompassing a whole directory and its contents, recursively.

    Not thread-safe.

    Args:
        templates_dir: Path of the directory containing the source templates.
        overwrite: Whether to silently overwrite output files if they already
            exist instead of the default behavior of raising an error.
        loader_factory: Custom :class:`~jinja2.BaseLoader`-returning callable,
            if you don't want to use Jinja's :class:`~jinja2.FileSystemLoader`
            for loading templates or want to intercept its instantiation. The
            returned loader must support both
            :meth:`~jinja2.BaseLoader.list_templates` and
            :meth:`~jinja2.BaseLoader.get_source`.
        environment_factory: Custom :class:`~jinja2.Environment`-returning
            callable, if you don't want to use Jinja's regular
            :class:`~jinja2.Environment` or want to intercept its
            instantiation. Will be given a list of extensions required for
            directory templating, the loader, and
            :attr:`~jinja2.Environment.keep_trailing_newline` is ``False`` as a
            more sensible default than Jinja's.
    """

    def __init__(
        self,
        templates_dir: Path | PathLike | str,
        overwrite: bool = False,
        loader_factory: Callable[..., BaseLoader] | None = None,
        environment_factory: Callable[..., Environment] | None = None,
    ):
        # normalize args
        self.templates_dir_path = (
            templates_dir
            if isinstance(templates_dir, Path)
            else Path(templates_dir)
        )
        if loader_factory is None:
            loader_factory = FileSystemLoader
        if environment_factory is None:
            environment_factory = Environment
        # / normalize args
        self.overwrite = overwrite
        self.loader = loader_factory(self.templates_dir_path)
        self.environment = cast(
            ExtendedEnvironment,  # it becomes one due to the extensions
            environment_factory(
                loader=self.loader,
                extensions=extensions,
                keep_trailing_newline=True,
            ),
        )

    def render(
        self,
        output_dir: Path | PathLike | str,
        /,
        *args: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        """
        Render a source (template) directory to an output directory.

        Args:
            output_dir: Path of the directory into which to place the output
                files.
            *args: If used, must contain a single mapping of template
                parameters (like Jinja's own :meth:`Template.render()
                <jinja2.Template.render>`).
            **kwargs: Values for template parameters (like Jinja's own
                :meth:`Template.render() <jinja2.Template.render>`). Mutually
                exclusive with usage of ``*args``.

        Raises:
            TemplateLoadingError: If the template could not be loaded.
            TemplateRenderingError: If the template could not be rendered.
            TemplateOutputError: If the rendered template could not be output
                (written to disk).
        """
        # normalize args
        output_dir_path = (
            output_dir if isinstance(output_dir, Path) else Path(output_dir)
        )
        template_params: Mapping[str, Any]
        if len(args) > 0:
            if len(args) != 1:
                raise ValueError(
                    "given more than one positional argument, but only one "
                    "(containing a mapping of template parameters) is "
                    "supported"
                )
            if kwargs:
                raise ValueError(
                    "given both a positional argument and keyword arguments "
                    "to specify template parameters - please use only one or "
                    "the other"
                )
            template_params = args[0]
        else:
            template_params = kwargs
        # /normalize args
        for template_name in self.loader.list_templates():
            try:
                template = self.environment.get_template(template_name)
            except Exception as e:
                # just b/c Jinja doesn't have dbg logs or nice exceptions...
                raise TemplateLoadingError(
                    f"error loading template {template_name!r}"
                ) from e
            try:
                template.render(**template_params)
            except Exception as e:
                raise TemplateRenderingError(
                    f"error rendering template {template_name!r} with params "
                    f"{template_params!r}"
                ) from e
            try:
                for (
                    filename,
                    content,
                ) in self.environment.mondir.rendered_files_map.items():
                    output_path = output_dir_path / Path(filename).relative_to(
                        self.templates_dir_path
                    )
                    mkdir_parents_up_to(
                        output_path, output_dir_path, exist_ok=self.overwrite
                    )
                    with output_path.open("w" if self.overwrite else "x") as o:
                        o.write(content)
            except Exception as e:
                raise TemplateOutputError(
                    f"error writing output of template {template_name!r}"
                ) from e
            # we have to wipe this manually because AFAIK Jinja provides
            # nothing in the way of per-render state => easiest to do it
            # ourselves; this is also what makes this not thread-safe...
            self.environment.mondir = MondirData()
