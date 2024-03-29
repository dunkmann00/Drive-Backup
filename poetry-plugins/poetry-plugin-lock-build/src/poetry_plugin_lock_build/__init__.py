from cleo.events.console_events import COMMAND
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.event_dispatcher import EventDispatcher
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry.core.factory import Factory
from poetry.core.packages.dependency_group import DependencyGroup, MAIN_GROUP

from poetry_plugin_export.walker import get_project_dependency_packages

NAME = "poetry-plugin-lock-build"

class LockBuildPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        # Only run if the plugin is listed in the pyproject.toml
        if application.poetry.pyproject.data.get("tool", {}).get(NAME) is not None:
            application.event_dispatcher.add_listener(
                COMMAND, self.lock_build
            )

    def lock_build(
        self,
        event: ConsoleCommandEvent,
        event_name: str,
        dispatcher: EventDispatcher
    ) -> None:
        command = event.command
        if not isinstance(command, BuildCommand):
            return

        event.io.write_line(
            f"<info>Pinning dependencies with lockfile.</>"
        )

        project_package = command.poetry.package

        pinned_group = DependencyGroup(MAIN_GROUP)

        for dependency_package in get_project_dependency_packages(
            command.poetry.locker,
            project_package.requires,
            project_package.name,
            project_package.python_marker
        ):
            dependency = dependency_package.dependency
            package = dependency_package.package

            # If the dependency's python_constraint is the same as the project's
            # python_constraint, we don't actually need to include it in the build info.
            # In that case we exclude it and include whatever is left.
            marker = dependency.marker if dependency.python_constraint != project_package.python_constraint else dependency.marker.exclude("python_version")

            pinned_dep = Factory.create_dependency(
                package.name, # name = package name (i.e. balloons) 👍 , complete_name = package name + features (aka extras) (i.e. balloons[red]) 👎
                dict(version=str(package.version), markers=str(marker)),
                [pinned_group.name],
                project_package.root_dir
            )

            pinned_group.add_dependency(pinned_dep)

        project_package.add_dependency_group(pinned_group)
