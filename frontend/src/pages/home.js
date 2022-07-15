import React, { Component } from 'react'
import {
    Grid, Paper, Typography, IconButton, Tooltip, TextField, AppBar, Tabs, Tab, Switch
} from '@material-ui/core'
import { withRouter } from "react-router-dom"
import { withTheme } from '@material-ui/core/styles'
import { AddCircleOutline } from '@material-ui/icons'
import { BASE_URL } from "../utils/environment"
import { get, post } from "../utils/requests"

const CAMERA_OFFLINE_IMG = "/offline_sn.png"

const CameraView = (props) => {
    return (
        <Grid item xs={6} key={`${props.cam.url}`}>
            <img
                src={`${props.cam.url}/video.mjpg`}
                id={`${props.cam.url}`}
                style={{ width: '100%' }}
                onError={(e) => { document.getElementById(props.cam.url).src = CAMERA_OFFLINE_IMG }}

            />
            <Switch
                name='audio'
                value={props.cam.config.audio}
            />
            <Switch
                name='back_cam'
                value={props.cam.config.back_cam}
            />
            <Switch
                name='crop'
                value={props.cam.config.crop}
            />

            <TextField select
            >
                {[]}
            </TextField>
            <Switch
                name='ts'
                value={props.cam.config.ts}
            />

            <Typography variant='caption' >{props.cam.url}</Typography>
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
        }
    }

    componentDidMount() {
        this.getCameras()
    }

    async getCameras() {
        try {
            const cameras = await get(`${BASE_URL}/cameras/`)
            console.log('Cameras', cameras)
            this.setState({ cameras: cameras })
        } catch (e) {
            console.log(e)
        }

    }

    async addCamera(value) {
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

    render() {
        return (
            <Grid xs={12} item>
                <AddCamera
                    listenEnter={this.listenEnter.bind(this)}
                />

                <Grid item container xs={12}>
                    {this.state.cameras.map(cam => {
                        return (<CameraView cam={cam} />)
                    })}
                </Grid>
            </Grid>
        )
    }
}


HomePage = withRouter(withTheme(HomePage))
export { HomePage }