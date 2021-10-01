install_data('org.danctnix.Tweaks.desktop',
    install_dir: join_paths(get_option('datadir'), 'applications'),
)

install_data(['org.danctnix.Tweaks.appdata.xml'],
             install_dir : get_option('datadir') / 'metainfo')

install_data('org.danctnix.Tweaks.svg',
    install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data('org.danctnix.Tweaks.policy',
  install_dir: join_paths(get_option('datadir'), 'polkit-1/actions')
)

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('bindir', get_option('bindir'))


install_data(['danctnix-tweakd.service'],
    install_dir: '/usr/lib/systemd/system')
