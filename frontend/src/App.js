import React from "react";
import {
  Switch, Route, BrowserRouter
} from 'react-router-dom';
import {
  createTheme, withStyles, withTheme, ThemeProvider, responsiveFontSizes
} from '@material-ui/core/styles';
import {
  Grid, IconButton, Typography, ClickAwayListener
} from '@material-ui/core';
import DateFnsUtils from '@date-io/date-fns';

import { MuiPickersUtilsProvider } from '@material-ui/pickers';
import CloseIcon from '@material-ui/icons/Close';
import darkTheme from "./css/darkTheme"
import pdftheme from "./css/pdfTheme"
import lightTheme from "./css/lightTheme"


import { HomePage } from "./pages/home"
import { BASE_URL } from "./utils/environment"
import "./App.css"


const AlertGrid = withStyles(theme => ({
  root: {
    position: "fixed",
    top: 0,
    display: 'flex', // make us of Flexbox
    alignItems: 'center', // does vertically center the desired content
    justifyContent: 'center', // horizontally centers single line items
    textAlign: 'center',
    width: '98vw',
    zIndex: '10000 !important'

  }
}))(Grid)

const GreenGrid = withStyles(theme => ({
  root: {
    backgroundColor: '#f4f9f6',
    border: '3px solid #0aa653',
    borderRadius: '8px',
    marginTop: '64px',
    color: '#0aa653',
    minHeight: '75px',
  }
}))(Grid)

const RedGrid = withStyles(theme => ({
  root: {
    backgroundColor: '#f9f4f4',
    border: '3px solid #a60a0a',
    borderRadius: '8px',
    marginTop: '64px',
    color: '#a60a0a',
    minHeight: '75px',
  }
}))(Grid)


const SeverityAlert = withTheme((props) => {
  const Inner = () => {
    return (
      <Grid item container justifyContent='center' alignItems='center' xs={12}>
        <Grid item xs={10}>
          <Typography variant='h6' style={{ color: 'inherit' }}>
            {props.msg}
          </Typography>
        </Grid>
        <Grid item xs={2}>
          <IconButton onClick={props.onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Grid>
      </Grid>
    )
  }


  return (
    <ClickAwayListener onClickAway={props.onClose}>
      <AlertGrid item xs={12}>
        <Grid item xs={3}></Grid>
        <Grid item xs={6}>
          {
            props.severity === 'success' ?
              <GreenGrid item container xs={12}>
                <Inner props={props} />
              </GreenGrid>

              :
              <RedGrid item container xs={12}>
                <Inner props={props} />
              </RedGrid>
          }
        </Grid>
        <Grid item xs={3}></Grid>
      </AlertGrid>
    </ClickAwayListener>
  )
})

const BackgroundGrid = withStyles(theme => ({
  root: {
    backgroundColor: theme.palette.background.paper,
    position: "absolute",
    minHeight: "100vh",
    maxHeight: "100vh",
    overflowY: "auto"
  }
}))(Grid)

const breakPoints = ['xs', 'sm', 'md', 'lg', 'xl']
let DarkTheme = responsiveFontSizes(createTheme(darkTheme), breakPoints)
let PdfTheme = responsiveFontSizes(createTheme(pdftheme), breakPoints)
let LightTheme = responsiveFontSizes(createTheme(lightTheme), breakPoints)



export default class App extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      user: {},
      theme: DarkTheme,
      showAlert: false,
      alertSeverity: '',
      alertMsg: '',
    }
  }

  static getDerivedStateFromProps(props, state) {
    return state
  }

  componentDidMount() {
    // this.listenUser()
    this.delayedClose()
  }


  // listenUser() {
  //   auth.onAuthStateChange((user) => {
  //     if (user) {
  //       this.setState({ user })
  //     } else {
  //       this.setState({ user: {} })
  //     }
  //   });
  // }

  onAlert(alertMsg, alertSeverity) {
    this.setState({ alertMsg: alertMsg, alertSeverity: alertSeverity, showAlert: true })
    // this.delayedClose()
  }

  delayedClose() {
    new Promise(resolve => setTimeout(resolve, 2100))
      .then(() => {
        this.onCloseAlert()
      })
  }
  onCloseAlert() {
    this.setState({ showAlert: false })
  }

  // onLogin(user) {
  //   this.setState({ user })
  // }

  toggleTheme(theme) {
    let newTheme = theme === 'Dark' ? DarkTheme : theme === 'Light' ? LightTheme : DarkTheme
    this.setState({ theme: newTheme })
  }

  render() {
    return (
      <BrowserRouter >
        <ThemeProvider theme={this.state.theme}>
          {
            this.state.showAlert ?
              <SeverityAlert
                onClose={this.onCloseAlert.bind(this)}
                severity={this.state.alertSeverity}
                msg={this.state.alertMsg} />
              :
              <React.Fragment></React.Fragment>

          }
          {/* {this.state.user && this.state.user.pk ? */}
          <MuiPickersUtilsProvider utils={DateFnsUtils}>
            <Switch>
              <Route exact path="/">
                <BackgroundGrid container direction="column" alignItems="center">
                  <Grid item container xs={12}
                    style={{
                      minHeight: "100%",
                      paddingTop: "8px",
                      paddingLeft: "8px",
                      paddingRight: "8px"
                    }}
                  >
                    <HomePage
                      BASE_URL={BASE_URL}
                      // toggleTheme={this.toggleTheme.bind(this)}
                      onAlert={this.onAlert.bind(this)}
                    />

                  </Grid>
                </BackgroundGrid>
              </Route>


              {/* <Route path="/adminDashboard">
                  <BackgroundGrid container direction="column" alignItems="center">
                    <AdminDashboard
                      onAlert={this.onAlert.bind(this)}
                      toggleTheme={this.toggleTheme.bind(this)}
                    />
                  </BackgroundGrid>
                </Route> */}

            </Switch>
          </MuiPickersUtilsProvider>
          {/* //   :
          //   <Login
          //     onLogin={this.onLogin.bind(this)}
          //     onAlert={this.onAlert.bind(this)}
          //   />
          // } */}
        </ThemeProvider>
      </BrowserRouter>
    )
  }
}