import React, { Component } from 'react'
import {
    Grid, Paper, Typography, IconButton, Tooltip, TextField, AppBar, Tabs, Tab, Switch
} from '@material-ui/core'
import { withRouter } from "react-router-dom"
import { withTheme } from '@material-ui/core/styles'
import { AddCircleOutline, Album, DeleteForever, GetApp, RemoveCircle, Stop } from '@material-ui/icons'
import { BASE_URL } from "../utils/environment"
import { get, post, del_ete, getVideo } from "../utils/requests"
import ActionCancelModal from "../comps/modals/actionCancelModal"

const CAMERA_OFFLINE_IMG = "/offline_sn.png"

const CameraFileRow = (props) => {
    return (
        <Grid item xs={12} style={{ paddingLeft: "8px", }}>
            <Typography variant='caption' color='secondary'> {props.displayName.split("_")[1]} </Typography>


            <Tooltip title='Download Video'>
                <IconButton onClick={() => props.onDownload(props.filename)}>
                    <GetApp color='primary' />
                </IconButton>
            </Tooltip>

            <Tooltip title='Delete Video' style={{ paddingLeft: "20vw" }}>
                <IconButton onClick={() => props.onDeleteVideo(props.filename)}>
                    <RemoveCircle color='error' />
                </IconButton>
            </Tooltip>
        </Grid>
    )
}


class CameraVideos extends Component {
    constructor(props) {
        super()
        this.state = {
            filenames: {}
        }

    }
    componentDidMount() {
        this.getFilenames()
    }

    componentDidUpdate(prevProps, prevState) {
        console.log("Comp did update")
        console.log(this.props)
        console.log(prevProps)
        if (this.props.is_rec !== prevProps.is_rec) {
            this.getFilenames()
        }
    }

    async getFilenames() {
        console.log("getting video list for url: ", this.props.url)
        const filenames = await get(`${BASE_URL}/cameras/get_videos/?url=${encodeURIComponent(this.props.url)}`)

        this.setState({ filenames })
    }

    async onDownload(filename) {
        console.log("Downloading ", filename, this.props.url)
        try {
            const blob = await getVideo(`${BASE_URL}/cameras/download_video/?filename=${encodeURIComponent(filename)}`)
            console.log("Video blob: ", blob)
            let url = window.URL.createObjectURL(blob);
            let a = document.createElement("a");
            console.log(url);
            a.href = url;
            a.download = filename;
            a.click();

        } catch (e) {
            console.log("Failed downloading", e)
        }
    }

    async onDeleteVideo(filename) {
        console.log("Deleting ", filename, this.props.url)
        try {
            if (await post(`${BASE_URL}/cameras/remove_videos/`, { url: this.props.url, filename })) {
                this.getFilenames()
            } else {
                console.log("Failed to delete")
            }

        } catch (e) {
            console.log("Failed deleting", e)
        }
    }

    render() {
        return (
            <Grid container item xs={12}>
                <Typography variant='caption' color='primary'>Recordings</Typography>

                {Object.keys(this.state.filenames).length > 0 ?
                    Object.keys(this.state.filenames).map(filename => {
                        return (
                            <CameraFileRow filename={filename}
                                displayName={this.state.filenames[filename]}
                                onDownload={this.onDownload.bind(this)}
                                onDeleteVideo={this.onDeleteVideo.bind(this)}
                            />
                        )
                    })
                    :
                    <React.Fragment>No videos recorded</React.Fragment>
                }
            </Grid>
        )
    }
}



const CameraView = (props) => {
    console.log("single cam: ", props.cam)
    return (
        <Grid item container xs={6} key={`${props.cam.url}`}>
            <Paper elevation={4} style={{ border: "1px solid white", width: "100%" }}>
                <Grid item container xs={12}>
                    <Grid item xs={12}>
                        <img
                            src={`${props.cam.url}/video.mjpg`}
                            id={`${props.cam.url}`}
                            style={{ width: '100%', maxHeight: "85vh" }}
                            onError={(e) => { document.getElementById(props.cam.url).src = CAMERA_OFFLINE_IMG }}

                        />
                    </Grid>
                    <Grid item xs={12} align='right'>
                        <Typography variant='bod1' style={{ paddingRight: "20px", minWidth: "100%" }}>{props.cam.url}</Typography>
                    </Grid>
                    <Grid item xs={12} style={{ paddingLeft: "8px" }}>
                        <Typography variant='caption'> Flash </Typography>
                        <Switch
                            name='audio'
                            label="Flash"
                            checked={props.cam.config.flash}
                            onChange={() => props.onFlashToggle(props.cam.url)}
                        />
                        <Tooltip title='Start Recording'>
                            <IconButton onClick={() => props.onRecord(props.cam.url)}>
                                <Album color={props.cam.is_rec ? "error" : "primary"} />
                            </IconButton>
                        </Tooltip>
                        <Tooltip title='Stop Recording'>
                            <IconButton onClick={() => props.onStopRecord(props.cam.url)}>
                                <Stop color='secondary' />
                            </IconButton>
                        </Tooltip>

                        <Tooltip title='Remove Camera'>
                            <IconButton onClick={() => props.onDelete(props.cam.url)}>
                                <DeleteForever color='error' />
                            </IconButton>
                        </Tooltip>
                    </Grid>


                    <Grid item xs={12} style={{ paddingLeft: "8px" }}>
                        <CameraVideos url={props.cam.url} is_rec={props.cam.is_rec} />
                    </Grid>


                </Grid>
            </Paper>
        </Grid>
    )
}


const AddCameraRaw = (props) => {
    console.log(props.theme.palette.text.primary)
    return (
        <Paper>
            <Grid item container xs={12}>
                <Grid item xs={4}>
                    <TextField fullWidth
                        id="add_cam_field"
                        onKeyDown={props.listenEnter}
                        label='Add new camera'
                        color='primary'
                        placeholder='http://192.168.0.181'
                        variant='outlined'
                    />
                </Grid>
                <Grid item align="left" xs={8}>
                    <Tooltip title="Add Camera">
                        <IconButton onClick={(ev) => props.listenEnter({ keyCode: 13, target: { value: document.getElementById('add_cam_field').value } })}>
                            <AddCircleOutline color='primary' />
                        </IconButton>
                    </Tooltip>
                </Grid>
            </Grid>

        </Paper>
    )
}

const AddCamera = withTheme(AddCameraRaw)


class HomePage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            cameras: [],
            delCamUrl: "",
            showConfirmDelUrlModal: false,
            recordState: {},
        }
    }

    componentDidMount() {
        this.getCameras()
    }

    async getCameras() {
        try {
            const cameras = await get(`${BASE_URL}/cameras/`)
            console.log('Cameras', cameras)

            this.setState({ cameras: cameras.map(c => { c['is_rec'] = false; return c; }) })
        } catch (e) {
            console.log(e)
        }

    }

    addCamera(value) {
        post(`${BASE_URL}/cameras/`, { url: value })
            .then(res => {
                this.getCameras()
            })
    }


    listenEnter(ev) {
        const { name, value } = ev.target
        console.log("Keycode/ value", ev.keyCode, value)
        if (ev.keyCode === 13) {
            this.addCamera(value)
        }
    }

    onFlashToggle(url) {
        post(`${BASE_URL}/cameras/toggle_flash/`, url)
            .then(res => {
                console.log("Falsh is now on: ", res)
                const cameras = this.state.cameras
                const updated_cameras = cameras.map(cam => {
                    if (cam.url === url) {
                        cam.config.flash = res
                    }
                    return cam
                })

                this.setState({ cameras: updated_cameras })
            })
            .catch(err => {
                console.log(err)
            })
    }

    confirmDeleteCamera(url) {
        this.setState({ showConfirmDelUrlModal: true, delCamUrl: url })
    }

    toggleShowConfirmDelUrlModal(val) {
        this.setState({ showConfirmDelUrlModal: val })

    }

    strip_http(url) {
        return url.substring(7) // http://
    }

    onDelete() {
        console.log("Deleting ", this.state.delCamUrl)
        del_ete(`${BASE_URL}/cameras/0/`, this.state.delCamUrl)
            .then(res => {
                this.toggleShowConfirmDelUrlModal(false)
                this.getCameras()
            })
    }

    onRecord(url) {
        post(`${BASE_URL}/cameras/start_recording/`, url)
            .then(res => {
                console.log(url, " is now recording? ", res)
                if (res === "started") {
                    let cameras = this.state.cameras.map(cam => {
                        if (cam.url === url) {
                            cam['is_rec'] = true
                        }
                        return cam
                    })

                    this.setState({ cameras })
                }
            })
            .catch(err => {
                console.log(err)
            })
    }
    onStopRecord(url) {
        post(`${BASE_URL}/cameras/stop_recording/`, url)
            .then(res => {
                console.log(url, " is now stopped? ", res)
                if (res === "stopped") {
                    let cameras = this.state.cameras.map(cam => {
                        if (cam.url === url) {
                            cam['is_rec'] = false
                        }
                        return cam
                    })

                    this.setState({ cameras })
                }
            })
            .catch(err => {
                console.log(err)
            })
    }

    render() {
        return (
            <Grid xs={12} item>
                <AddCamera
                    listenEnter={this.listenEnter.bind(this)}
                />

                <Grid item container spacing={4} xs={12} style={{ paddingLeft: "24px" }}>
                    {this.state.cameras.map(cam => {
                        return (
                            <CameraView cam={cam}
                                onDelete={this.confirmDeleteCamera.bind(this)}
                                onFlashToggle={this.onFlashToggle.bind(this)}
                                onRecord={this.onRecord.bind(this)}
                                onStopRecord={this.onStopRecord.bind(this)}
                            />
                        )
                    })}
                </Grid>
                <ActionCancelModal
                    open={this.state.showConfirmDelUrlModal}
                    actionText="Delete"
                    cancelText="Cancel"
                    modalText={`Delete cam @ ${this.state.delCamUrl}?`}
                    onAction={this.onDelete.bind(this)}
                    onClose={() => this.toggleShowConfirmDelUrlModal(false)}

                />
            </Grid>
        )
    }
}


HomePage = withRouter(withTheme(HomePage))
export { HomePage }