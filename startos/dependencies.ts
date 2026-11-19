import { sdk } from './sdk'
import { i18n } from './i18n'
import { workspaceMinimumVersion, workspacePackageId } from './utils'

export const dependencies = sdk.Dependencies.of().addDependency(
  sdk.Dependency.required(workspacePackageId, {
    description: i18n(
      'Provides remote projects, development tools and containers.',
    ),
    metadata: {
      title: 'Dev Workspace',
      icon: 'assets/dependency-icons/dev-workspace.svg',
    },
    versionRange: workspaceMinimumVersion,
    kind: 'running',
    healthChecks: [],
  }),
)
