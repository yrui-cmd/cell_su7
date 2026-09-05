"""Make an isolated one-slide deck initially hidden for native path playback."""
import argparse
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}

def prepare(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target or target.exists():
        raise ValueError('Use a new output path; never overwrite an existing deck')
    with ZipFile(source) as archive:
        slides = [n for n in archive.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        if len(slides) != 1:
            raise ValueError('Playback requires an isolated single-slide drawing')
        root = E.fromstring(archive.read(slides[0]))
        shapes = root.findall('p:cSld/p:spTree/p:sp', NS)
        if not shapes:
            raise ValueError('No native paths found')
        if any(shape.find('p:nvSpPr/p:cNvPr', NS).get('hidden') in ('1', 'true') for shape in shapes):
            raise ValueError('Source contains intentionally hidden objects; use a clean drawing deck')
        for shape in shapes:
            shape.find('p:nvSpPr/p:cNvPr', NS).set('hidden', '1')
        with ZipFile(target, 'w') as output:
            for info in archive.infolist():
                output.writestr(info, E.tostring(root, xml_declaration=True, encoding='UTF-8') if info.filename == slides[0] else archive.read(info.filename))
    return len(shapes)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-pptx', required=True)
    parser.add_argument('--output-pptx', required=True)
    args = parser.parse_args()
    print(prepare(args.input_pptx, args.output_pptx))
