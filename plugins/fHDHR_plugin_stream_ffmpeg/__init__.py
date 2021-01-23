import sys
import subprocess

# from fHDHR.exceptions import TunerError

PLUGIN_NAME = "ffmpeg"
PLUGIN_VERSION = "v0.6.0-beta"
PLUGIN_TYPE = "alt_stream"


class FFMPEG_Setup():
    def __init__(self, config):
        try:
            ffmpeg_command = [config.dict["ffmpeg"]["path"],
                              "-version",
                              "pipe:stdout"
                              ]

            ffmpeg_proc = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)
            ffmpeg_version = ffmpeg_proc.stdout.read()
            ffmpeg_proc.terminate()
            ffmpeg_proc.communicate()
            ffmpeg_proc.kill()
            ffmpeg_version = ffmpeg_version.decode().split("version ")[1].split(" ")[0]
        except FileNotFoundError:
            ffmpeg_version = "Missing"
            print("Failed to find ffmpeg.")
        config.register_version("ffmpeg", ffmpeg_version)


class FFMPEG_Stream():

    def __init__(self, fhdhr, stream_args, tuner):
        self.fhdhr = fhdhr
        self.stream_args = stream_args
        self.tuner = tuner

        self.bytes_per_read = int(self.fhdhr.config.dict["streaming"]["bytes_per_read"])
        self.ffmpeg_command = self.ffmpeg_command_assemble(stream_args)

    def get(self):

        ffmpeg_proc = subprocess.Popen(self.ffmpeg_command, stdout=subprocess.PIPE)

        def generate():
            try:
                while self.tuner.tuner_lock.locked():

                    chunk = ffmpeg_proc.stdout.read(self.bytes_per_read)
                    if not chunk:
                        break
                        # raise TunerError("807 - No Video Data")
                    yield chunk
                    chunk_size = int(sys.getsizeof(chunk))
                    self.tuner.add_downloaded_size(chunk_size)
                self.fhdhr.logger.info("Connection Closed: Tuner Lock Removed")

            except GeneratorExit:
                self.fhdhr.logger.info("Connection Closed.")
            except Exception as e:
                self.fhdhr.logger.info("Connection Closed: %s" % e)
            finally:
                ffmpeg_proc.terminate()
                ffmpeg_proc.communicate()
                ffmpeg_proc.kill()
                self.fhdhr.logger.info("Connection Closed: Tuner Lock Removed")
                self.tuner.close()
                # raise TunerError("806 - Tune Failed")

        return generate()

    def ffmpeg_command_assemble(self, stream_args):
        ffmpeg_command = [
                          self.fhdhr.config.dict["ffmpeg"]["path"],
                          "-i", stream_args["stream_info"]["url"],
                          ]
        ffmpeg_command.extend(self.ffmpeg_headers(stream_args))
        ffmpeg_command.extend(self.ffmpeg_duration(stream_args))
        ffmpeg_command.extend(self.transcode_profiles(stream_args))
        ffmpeg_command.extend(self.ffmpeg_loglevel())
        ffmpeg_command.extend(["pipe:stdout"])
        return ffmpeg_command

    def ffmpeg_headers(self, stream_args):
        ffmpeg_command = []
        if stream_args["stream_info"]["headers"]:
            headers_string = ""
            if len(list(stream_args["stream_info"]["headers"].keys())) > 1:
                for x in list(stream_args["stream_info"]["headers"].keys()):
                    headers_string += "%s: %s\r\n" % (x, stream_args["stream_info"]["headers"][x])
            else:
                for x in list(stream_args["stream_info"]["headers"].keys()):
                    headers_string += "%s: %s" % (x, stream_args["stream_info"]["headers"][x])
            ffmpeg_command.extend(["-headers", '\"%s\"' % headers_string])
        return ffmpeg_command

    def ffmpeg_duration(self, stream_args):
        ffmpeg_command = []
        if stream_args["duration"]:
            ffmpeg_command.extend(["-t", str(stream_args["duration"])])
        else:
            ffmpeg_command.extend(
                                  [
                                   "-reconnect", "1",
                                   "-reconnect_at_eof", "1",
                                   "-reconnect_streamed", "1",
                                   "-reconnect_delay_max", "2",
                                  ]
                                  )

        return ffmpeg_command

    def ffmpeg_loglevel(self):
        ffmpeg_command = []
        log_level = self.fhdhr.config.dict["logging"]["level"].lower()

        loglevel_dict = {
                        "debug": "debug",
                        "info": "info",
                        "error": "error",
                        "warning": "warning",
                        "critical": "fatal",
                        }
        if log_level not in ["info", "debug"]:
            ffmpeg_command.extend(["-nostats", "-hide_banner"])
        ffmpeg_command.extend(["-loglevel", loglevel_dict[log_level]])
        return ffmpeg_command

    def transcode_profiles(self, stream_args):

        if stream_args["transcode_quality"]:
            self.fhdhr.logger.info("Client requested a %s transcode for stream." % stream_args["transcode_quality"])

        ffmpeg_command = []

        if not stream_args["transcode_quality"] or stream_args["transcode_quality"] == "heavy":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-f", "mpegts"
                                    ])

        elif stream_args["transcode_quality"] == "mobile":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-s", "1280X720",
                                    "-b:v", "500k",
                                    "-b:a", "128k",
                                    "-f", "mpegts"
                                    ])

        elif stream_args["transcode_quality"] == "internet720":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-s", "1280X720",
                                    "-b:v", "1000k",
                                    "-b:a", "196k",
                                    "-f", "mpegts"
                                    ])

        elif stream_args["transcode_quality"] == "internet480":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-s", "848X480",
                                    "-b:v", "400k",
                                    "-b:a", "128k",
                                    "-f", "mpegts"
                                    ])

        elif stream_args["transcode_quality"] == "internet360":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-s", "640X360",
                                    "-b:v", "250k",
                                    "-b:a", "96k",
                                    "-f", "mpegts"
                                    ])

        elif stream_args["transcode_quality"] == "internet240":
            ffmpeg_command.extend([
                                    "-c", "copy",
                                    "-s", "432X240",
                                    "-b:v", "250k",
                                    "-b:a", "96k",
                                    "-f", "mpegts"
                                    ])

        return ffmpeg_command