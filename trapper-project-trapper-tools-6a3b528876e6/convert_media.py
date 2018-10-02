#!/usr/bin/python
import os
import re
import logging
import datetime
from optparse import OptionParser, make_option
from subprocess import Popen, PIPE

logging.basicConfig(
    format='%(levelname)s:%(message)s',
    level=logging.DEBUG
)
logging.getLogger().addHandler(logging.FileHandler('convert_media.log'))


class ConvertMedia(object):

    def __init__(
            self, media_root, keep_mdt, src_ext, convert2mp4,
            convert2webm, overwrite, FFMPEG='ffmpeg',
            move_converted=False, move_path = None 
    ):
        if not os.path.isdir(media_root):
            raise Exception('There is no directory: %s' % media_root)
        else:
            self.media_root = media_root
        self.keep_mdt = keep_mdt
        self.src_ext = src_ext
        self.convert2mp4 = convert2mp4
        self.convert2webm = convert2webm
        self.overwrite = overwrite
        self.FFMPEG = FFMPEG
        self.move_converted = move_converted
        self.move_path = move_path

    def replace_ext(self, filepath, ext):
        ext = ext.split('.')[-1]
        base = os.path.splitext(filepath)[0]
        return '.'.join([base, ext])

    def filter_files(self, filenames):
        regexp = '.*\.?{src_ext}'.format(
            src_ext=self.src_ext,
        )
        return [
            k for k in filenames if re.match(
                regexp, k, re.IGNORECASE
            )
        ]

    def handle(self):
        matches = []
        logging.info('Looking for %s files..', self.src_ext)
        for root, dirnames, filenames in os.walk(self.media_root):
            for filename in self.filter_files(filenames):
                matches.append(os.path.join(root, filename))
        logging.info('Found %s files.', len(matches))
        logging.info('')

        i = 1
        for video in matches:
            logging.info('[%s] Original file:\n%s', i, video)
            
            outfile = video
            if self.move_converted and os.path.isdir(self.move_path):
                outfile = os.path.join(
                    self.move_path, os.path.relpath(outfile, self.media_root)
                )
                if not os.path.isdir(os.path.dirname(outfile)):
                    os.makedirs(os.path.dirname(outfile))

            # "mp4" conversion
            if self.convert2mp4:
                outfile = self.replace_ext(outfile, 'mp4')
                if not os.path.isfile(outfile) or self.overwrite:
                    if self.overwrite:
                        logging.warning(
                            'The file: %s already exists but te "overwrite" '
                            'flag has been set. Overwritting..',
                            outfile
                        )
                    logging.info('[%s] Converting to mp4 file:\n%s', i, outfile)
                    ffmpeg_mp4 = (
                        '{ffmpeg} -y -i "{source}" -preset fast '
                        '-pix_fmt yuv420p '
                        '-vcodec libx264 -b:v 750k '
                        '-c:a aac -strict -2 -ac 2 '  
                        '-movflags faststart -qmin 10 -qmax 42 '
                        '-keyint_min 150 -g 150 '
                        '-loglevel error -nostats '
                        '"{outfile}"'
                        ).format(
                            ffmpeg = self.FFMPEG,
                            source = video,
                            outfile = outfile
                        )
                    logging.info('Subprocess: {cmd}'.format(cmd=ffmpeg_mp4))
                    p = Popen(ffmpeg_mp4, stdout=PIPE, stderr=PIPE, shell=True)
                    stdout, stderr = p.communicate()
                    if stderr:
                        logging.error('Subprocess failed:')
                        logging.error(stderr)
                    if self.keep_mdt:
                        mdt_original = datetime.datetime.utcfromtimestamp(
                            os.path.getmtime(video)
                        )
                        timestamp = (
                            mdt_original - datetime.datetime(1970, 1, 1)
                        ).total_seconds()
                        os.utime(
                            outfile,
                            (timestamp, timestamp)
                        )
                else:
                    logging.warning(
                        'The file: %s already exists. Skipping..',
                        outfile
                    )

            # "webm" conversion
            if self.convert2webm:
                outfile = self.replace_ext(outfile, 'webm')
                if not os.path.isfile(outfile) or self.overwrite:
                    if self.overwrite:
                        logging.warning(
                            'The file: %s already exists but the "overwrite" '
                            'flag has been set. Overwritting..',
                            outfile
                        )
                    logging.info('[%s] Converting to webm file:\n%s', i, outfile)
                    ffmpeg_webm = (
                        '{ffmpeg} -y -i "{source}" '
                        '-codec:v libvpx '
                        '-codec:a vorbis -strict -2 -ac 2 -b:a 128k ' 
                        # -cpu-used => a critical parameter related
                        # to a speed of conversion
                        '-quality good -cpu-used 5 '
                        '-qmin 0 -qmax 45 '
                        '-keyint_min 150 -g 150 '
                        '-loglevel error -nostats '
                        '"{outfile}"'
                        ).format(
                            ffmpeg = self.FFMPEG,
                            source = video,
                            outfile = outfile
                        )
                    logging.info('Subprocess: {cmd}'.format(cmd=ffmpeg_webm))
                    p = Popen(ffmpeg_webm, stdout=PIPE, stderr=PIPE, shell=True)
                    stdout, stderr = p.communicate()
                    if stderr:
                        logging.error('Subprocess failed:')
                        logging.error(stderr)
                    if self.keep_mdt:
                        mdt_original = datetime.datetime.utcfromtimestamp(
                            os.path.getmtime(video)
                        )
                        timestamp = (
                            mdt_original - datetime.datetime(1970, 1, 1)
                        ).total_seconds()
                        os.utime(
                            outfile,
                            (timestamp, timestamp)
                        )
                else:
                    logging.warning(
                        'The file: %s already exists. Skipping..',
                        outfile
                    )
            i = i + 1


def main():
    title = 'Batch conversion of videos with ffmpeg'
    usage = 'Usage: %prog [options] media_root'
    option_list = [
        make_option(
            '--source-extension',
            action='store',
            dest='src_ext',
            default='.AVI',
            help='Extension of source files (default: .AVI).'
        ),
        make_option(
            '--keep-modification-timestamp',
            action='store_true',
            dest='keep_mdt',
            help='Keep the modification timestamp of source files.'
        ),
        make_option(
            '--convert2mp4',
            action='store_true',
            dest='convert2mp4',
            help='Convert to "mp4".'
        ),
        make_option(
            '--convert2webm',
            action='store_true',
            dest='convert2webm',
            help='Convert to "webm".'
        ),
        make_option(
            '--overwrite',
            action='store_true',
            dest='overwrite',
            help='When convered file already exists overwrite it.'
        ),
        make_option(
            '--FFMPEG',
            action='store',
            dest='FFMPEG',
            default='ffmpeg',
            help='Path to ffmpeg (default: ffmpeg).'
        ),
        make_option(
            '--move_converted',
            action='store_true',
            dest='move_converted',
            help='Move converted files to "move_path"'
        ),
        make_option(
            '--move_path',
            action='store',
            dest='move_path',
            default=None,
            help='Where to move converted files (default: None).'
        ),

    ]
    parser = OptionParser(usage, option_list=option_list)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Incorrect number of arguments.")
    logging.info('')
    logging.info(
        'Media converter started at %s',
        datetime.datetime.now()
    )
    logging.info('Media path: %s', args[0])
    logging.info('FFMPEG: %s', options.FFMPEG)
    logging.info('')
    cm = ConvertMedia(
        media_root=args[0],
        keep_mdt=options.keep_mdt,
        src_ext=options.src_ext,
        convert2mp4=options.convert2mp4,
        convert2webm=options.convert2webm,
        overwrite=options.overwrite,
        FFMPEG=options.FFMPEG,
        move_converted = options.move_converted,
        move_path = options.move_path
    ).handle()


if __name__ == "__main__":
    main()

    
