# postmarketOS tweaks

This is a mobile gtk3 application for tweaking settings on desktop environments supported by postmarketOS. 

![](https://brixitcdn.net/metainfo/tweaks.png)

The tweakable settings are defined in yaml formatted config files in `/usr/share/postmarketos-tweaks` and
`/etc/postmarketos-tweaks`.

## Setting definition file format

The settings are organized in a tree with 3 levels: page, section and setting. All the config files are read and
pages/sections with the same name are merged. All pages/sections/settings are sorted according to the weight if set.

```yaml
- name: the page name
  weight: the page weight
  sections:
    - name: the section name
      weight: the section weight
      settings:
        - name: The setting name
          weight: the setting weight
          help: The setting description
          type: the widget type to show
          backend: The storage backend for this setting
```

### Backends

The application supports multiple backends to store/read settings from. Most of the settings in Tweaks are stored in the
gsettings backend.

### Generic options

*type*: The widget type to create for the setting, one of:

* boolean: gets rendered as a switch
* choice: a dropdown with the options defined by the `map` option
* number: gets rendered as a number textfield
* font: the OS font picker

*map*: Mapping between the setting in the backend and the setting in the UI. Can be used to define the options for a
choice or make a boolean option store a specific string in the backend.

```yaml
map:
  Display value 1: stored-value1
  Display value 2: stored-value2

# for a boolean
map:
  true: suspend
  false: nothing
```

*min, max, step*: Sets the range for a number widget and the step value for the [+] and [-] keys in the widget.

*percentage: true*: Remaps the min,max value for a number field to 0-100. It's basically like `map:` but for setting
the whole number range.

### gsettings

```yaml
backend: gsettings
gtype: boolean
key: org.postmarketos.Tweaks.coolsetting
```

Uses gsettings to read and write the settings. The `key` is the full path to the setting. It's possible to set the key
to a list of settings in which case the first one found will be used.

The `gtype` option is used to define which type the gsetting is in case it's different than the type of the widget. This
is mainly useful when things are remapped.

### gtk3settings

```yaml
type: boolean
backend: gtk3settings
key: gtk-application-prefer-dark-theme
default: "0"
map:
  true: "1"
  false: "0"
```

This is a backend for modifying the `~/.config/gtk-3.0/settings.ini` file. The key is the name of the setting inside the 
`[Settings]` section.

### sysfs

```yaml
backend: sysfs
key: /sys/class/power_supply/axp20x-battery/voltage_max_design
stype: int
multiplier: 1000000
```

Used to set settings at runtime in sysfs, the tweakd background daemon will get the root permissions to actually change
the setting and re-apply the setting after booting.

The `stype` is the type of the variable that will be written, currently only `int` is supported. The multiplier is used
to get the final integer value to write since floats are stored as integers with a multiplier in the kernel. The multiplier
defaults to 1.

### symlink

```yaml
backend: symlink
key: ~/.local/var/example.data
source_ext: false
```

This creates a symlink where the source is the input data from the user and the target is the `key`.

If `source_ext` is true the extension of the source file will be appended to the key before using that as the target
path for the symlink.

Setting the value to `None` will remove the symlink.

This backend is normally used with the file widget.

### soundtheme

```yaml
backend: soundtheme
key: ~/.local/share/sounds/__custom/phone-incoming-call
```

The soundtheme is the same as the `symlink` backend. The `source_ext` parameter is always true with this backend.

It also ensures that the `index.theme` file exists in the same directory as the symlink to make it a valid custom sound
theme.

### file

```yaml
backend: file
key: ~/.config/example-file
needs-root: false
trailing-newline: true
```

The file backend is for writing plain text to a file without any parsing. The `key` is the filename to write.

The `needs-root` argument signifies that the file needs root permissions to write to. This will defer the writing to
tweakd. Expanduser is not used in this case since tweakd runs as root.

The `trailing-newline` setting defaults to true, if this is set a newline will be added at the end of the file and
removed again on reading.