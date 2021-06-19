arm_manufacturer = {
    'rockchip': 'Rockchip',
    'allwinner': 'Allwinner',
    'qcom': 'Qualcomm',
    'ti': 'Texas Instruments',
    'fsl': 'NXP',
}


def get_soc_name(manufacturer, part):
    result = ''
    if manufacturer in arm_manufacturer:
        result += arm_manufacturer[manufacturer]
    else:
        result += manufacturer.title()

    result += ' '

    if manufacturer == 'allwinner':
        temp = part.split('-')
        result += temp[-1].upper()
    elif manufacturer == 'fsl':
        part = part.upper()
        part = part.replace('IMX', 'i.MX ')
        result += part
    else:
        result += part.upper()

    return result
