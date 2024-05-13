from cleo.events.console_events import COMMAND
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.event_dispatcher import EventDispatcher
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.utils.extras import get_extra_package_names

from poetry.core.factory import Factory
from poetry.core.packages.dependency_group import DependencyGroup, MAIN_GROUP
from poetry.core.version.markers import SingleMarker

from poetry_plugin_export.walker import get_project_dependency_packages

from packaging.utils import canonicalize_name


NAME = "poetry-plugin-pin-build"

class PinBuildPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        application.event_dispatcher.add_listener(
            COMMAND, self.pin_build
        )

    def pin_build(
        self,
        event: ConsoleCommandEvent,
        event_name: str,
        dispatcher: EventDispatcher
    ) -> None:
        command = event.command
        if not isinstance(command, BuildCommand):
            return

        # Only run if the plugin is listed in the pyproject.toml
        if command.poetry.pyproject.data.get("tool", {}).get(NAME) is None:
            return

        event.io.write_line(
            f"<info>Pinning dependencies with lockfile.</>"
        )

        project_package = command.poetry.package

        # We are not directly adding to the group so we can check if a
        # dependency was already handled. There are two reasons to do this:
        # 1) It seems that if a dependency is listed and then required again by
        # another dependency, it can get listed multiple times when extras are
        # involved. So if we depend on 'cryptography[ssh]', and
        # 'drive-backup-credentials' depends on 'cryptography', cryptography
        # will get listed twice. Since we don't want this, we check to see if a
        # dependency has already been added.
        # 2) In order to handle our own sets of extras, we need to process
        # through all the dependencies for no extras first, and then each
        # different extra group. When doing this, dependencies could be part of
        # multiple groups of extras and/or the original non extra group. To make
        # sure the markers turn out correct, we need to keep combining markers
        # instead of overwriting the.
        pinned_dependencies = {}
        pinned_group = DependencyGroup(MAIN_GROUP)

        project_extras = [None] + list(project_package.extras.keys())

        for extra in project_extras:
            extra_deps = self.get_extras(command.poetry.locker, extra)

            for dependency_package in get_project_dependency_packages(
                command.poetry.locker,
                project_package.requires,
                project_package.name,
                project_package.python_marker,
                [extra] if extra is not None else []
            ):
                dependency = dependency_package.dependency
                package = dependency_package.package

                if extra_deps and package.name not in extra_deps:
                    continue # Handling extras but this package is not an extra, we don't need to keep processing

                # If the dependency's python_constraint is the same as the project's
                # python_constraint, we don't actually need to include it in the build info.
                # In that case we exclude it and include whatever is left.
                marker = dependency.marker if dependency.python_constraint != project_package.python_constraint else dependency.marker.exclude("python_version")

                if package.name in extra_deps:
                    marker = marker.intersect(SingleMarker("extra", f"=={extra}")) # Add the marker on

                pinned_dep = Factory.create_dependency(
                    package.name, # name = package name (i.e. balloons) 👍 , complete_name = package name + features (aka extras) (i.e. balloons[red]) 👎
                    dict(version=str(package.version), markers=str(marker)),
                    [pinned_group.name],
                    project_package.root_dir
                )

                if self.get_package_key(package) in pinned_dependencies:
                    other_pinned_dep = pinned_dependencies[self.get_package_key(package)]
                    pinned_dep.marker = pinned_dep.marker.union(other_pinned_dep.marker) # Combine the marker with previous ones
                pinned_dependencies[self.get_package_key(package)] = pinned_dep

        for pinned_dep in pinned_dependencies.values():
            pinned_group.add_dependency(pinned_dep)

        project_package.add_dependency_group(pinned_group)

    def get_package_key(self, package):
        return hash(package.name) ^ hash(package.version)

    def get_extras(self, locker, extra):
        if extra is None:
            return set()

        locked_repository = locker.locked_repository()
        locked_extras = {
            canonicalize_name(extra): [
                canonicalize_name(dependency) for dependency in dependencies
            ]
            for extra, dependencies in locker.lock_data.get("extras", {}).items()
        }

        package_extras = set()

        extra_package_names = get_extra_package_names(
            locked_repository.packages,
            locked_extras,
            [extra],
        )
        return set(extra_package_names)
