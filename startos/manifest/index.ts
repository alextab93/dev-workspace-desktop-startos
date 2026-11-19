import { setupManifest } from '@start9labs/start-sdk'
import { long, short } from './i18n'

export const manifest = setupManifest({
  id: 'dev-workspace-desktop',
  title: 'Dev Workspace Desktop',
  license: 'GPL-3.0-only',
  packageRepo: 'https://github.com/alextab93/dev-workspace-desktop-startos',
  upstreamRepo: 'https://github.com/linuxserver/docker-baseimage-selkies',
  marketingUrl: 'https://docs.linuxserver.io/selkies/',
  donationUrl: null,
  description: { short, long },
  volumes: ['main', 'config'],
  images: {
    desktop: {
      source: { dockerBuild: { workdir: '.' } },
      arch: ['x86_64', 'aarch64'],
      emulateMissing: false,
    },
  },
})
