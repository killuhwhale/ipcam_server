import React, { Component } from 'react'
// Material UI
import { Grid, Paper, Button, Typography, Modal, CircularProgress } from '@material-ui/core';
import { withTheme } from '@material-ui/core/styles';

class ActionCancelModal extends Component {
    constructor(props) {
        super(props)
        this.state = {
            open: props.open,
            loading: false
        }
        /*
        open
        actionText
        cancelText
        modalText
        onAction
        onClose
        */
    }

    static getDerivedStateFromProps(props, state) {
        return props
    }

    componentDidUpdate(prevProps, prevState) {
        if (prevState.open !== this.state.open) {
            this.setState({ loading: false })
        }
    }

    render() {
        return (
            <Modal
                open={this.state.open}
                onClose={this.props.onClose}
                aria-labelledby="simple-modal-title"
                aria-describedby="simple-modal-description">
                <div style={{
                    position: 'absolute',
                    top: "50%",
                    left: "50%",
                    width: "80vw",
                    transform: "translate(-50%, -50%)",
                }}>
                    <Grid
                        item
                        align="center"
                        xs={12}
                    >
                        <Paper style={{ height: "200px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                            <Grid item container xs={12}>
                                <Grid item xs={12}>
                                    <Typography variant="h6" style={{ marginTop: "32px" }}>
                                        {this.props.modalText}
                                    </Typography>
                                </Grid>
                                <Grid item xs={6}>
                                    <Button
                                        variant="outlined"
                                        onClick={() => { this.props.onClose() }}>
                                        {this.props.cancelText}
                                    </Button>
                                </Grid>
                                <Grid item xs={6}>
                                    {this.state.loading ? <CircularProgress /> :
                                        <Button
                                            color="primary"
                                            variant="outlined"
                                            onClick={() => { this.setState({ loading: true }); this.props.onAction(); }}>
                                            {this.props.actionText}
                                        </Button>
                                    }
                                </Grid>
                            </Grid>
                        </Paper>
                    </Grid>
                </div>
            </Modal>
        )
    }
}

export default ActionCancelModal = withTheme(ActionCancelModal); 