import { VersionGraph } from '@start9labs/start-sdk'
import { current } from './current'
import { v0_1_0_8 } from './0.1.0.8'
import { v0_1_0_7 } from './0.1.0.7'
import { v0_1_0_6 } from './0.1.0.6'
import { v0_1_0_5 } from './0.1.0.5'
import { v0_1_0_4 } from './0.1.0.4'
import { v0_1_0_3 } from './0.1.0.3'
import { v0_1_0_2 } from './0.1.0.2'
import { v0_1_0_0 } from './0.1.0.0'

export const versionGraph = VersionGraph.of({
  current,
  other: [
    v0_1_0_0,
    v0_1_0_2,
    v0_1_0_3,
    v0_1_0_4,
    v0_1_0_5,
    v0_1_0_6,
    v0_1_0_7,
    v0_1_0_8,
  ],
})
