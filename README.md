# motion_uploader
Motion daemon file uploader for the Microsoft OneDrive cloud service.
Consists of two suites
- motion_uploader_service - the service which runs the upload progress
- motion_uploader_auth - OAuth2 authenticator

Best to use with the supervisord.

## Sample supervisord config file
```
[program:motion_uploader]
user=motion
directory=/home/motion
command=/usr/local/bin/motion_uploader_service
stdout_logfile=/var/log/supervisor/motion_uploader-stdout
stdout_logfile_maxbytes=1MB
stderr_logfile=/var/log/supervisor/motion_uploader-stderr
stderr_logfile_maxbytes=1MB
autorestart=true
```

## Sample motion_uploader.ini file
```
cat /home/motion/motion_uploader.ini
[camera]
id = bedroom_floor1_window_1_left  # your camera identifier string

[app]
client_id = <your OAuth application UUID>
client_secret = <your OAuth application client secret>
redirect_uri = http://localhost

[refresh_token]
value = <your refresh token obtained from the motion_uploader_auth utility>
```

## How to use
1. Register an application within Microsoft Graph (One Drive). Specify redirect URI as http://localhost to be able to obtain the refresh_token in the command line
2. Create the motion_uploader.ini file, fill all the values, leave refresh_token.value empty
3. cd to the dir where motion_uploader.ini file resides and run the motion_uploader_auth utility
4. Follow the utility prompts (open the URL in the browser, authenticate your app to access your OneDrive account, obtain the tokens)
5. Copy the refresh_token value from the redirect URI in your browser and paste it to the refresh_token.value
6. Run your uploader daemon.

## Notes
- the application will create a root folder in your OneDrive, a camera id folder inside it and will uplod the images to the folders based on your local (!) datetime.
- the uploader scans the images in the current folder and selects to upload 10 most recent images, then scans again. This will ensure that the most recent footage is uploaded first in case of "intruder event".
- default timeout to upload one picture is 2 minutes, uploads taking longer will be cancelled and retried again.
- the default batch upload timeout is 30 minutes. This is because python3 http client may hang because of the internal InterruptedError handling. If the process hangs for longer it will be killed by SIGALRM so the upload process should be restarted by the "outside entity" (e.g. supervisord).
- 
