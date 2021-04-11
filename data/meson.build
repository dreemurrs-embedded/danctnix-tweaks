install_data('org.postmarketos.Tweaks.desktop',
    install_dir: join_paths(get_option('datadir'), 'applications'),
)

install_data(['org.postmarketos.Tweaks.appdata.xml'],
             install_dir : get_option('datadir') / 'metainfo')

install_data('org.postmarketos.Tweaks.svg',
    install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data('org.postmarketos.Tweaks.policy',
  install_dir: join_paths(get_option('datadir'), 'polkit-1/actions')
)

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('bindir', get_option('bindir'))

configure_file(
    input: 'postmarketos-tweakd.initd.in',
    output: 'postmarketos-tweakd',
    configuration: conf,
    install: true,
    install_dir: '/etc/init.d'
)
