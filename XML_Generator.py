import xml.etree.ElementTree as ET


def generate_new_settings_xml():
    pld = ET.Element('PLD')
    target_carousel = ET.SubElement(pld, 'target_carousel')

    targets = []
    sizes = []
    compositions = []
    heights = []
    util = []

    for i in range(0, 6):
        targets.append(ET.SubElement(target_carousel, 'target'))
        targets[i].set('ID', str(i))
        sizes.append(ET.SubElement(targets[i], 'Size'))
        compositions.append(ET.SubElement(targets[i], 'Composition'))
        heights.append(ET.SubElement(targets[i], 'Height'))
        util.append(ET.SubElement(targets[i], 'Utilization'))
        sizes[i].text = str(i)
        compositions[i].text = 'Blank' + str(i)
        heights[i].text = str(i)
        util[i].text = str(0.90)

    substrate = {'root': ET.SubElement(pld, 'substrate')}
    substrate['max_speed'] = ET.SubElement(substrate['root'], 'max_speed')
    substrate['max_speed'].text = '2000'
    substrate['acceleration'] = ET.SubElement(substrate['root'], 'acceleration')
    substrate['acceleration'].text = '2000000'

    target = {'root': ET.SubElement(pld, 'target')}
    target['max_speed'] = ET.SubElement(target['root'], 'max_speed')
    target['max_speed'].text = '2000'
    target['acceleration'] = ET.SubElement(target['root'], 'acceleration')
    target['acceleration'].text = '2000000'

    laser = {'root': ET.SubElement(pld, 'laser')}
    laser['max_reprate'] = ET.SubElement(laser['root'], 'max_reprate')
    laser['max_reprate'].text = '20'

    tree = ET.ElementTree(pld)

    tree.write('settings.xml')
    ET.dump(pld)
