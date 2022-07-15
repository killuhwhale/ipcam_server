import appTheme from './baseTheme'

let blkOrWhite = false ? "#000" : '#fff'
let backgroundColor = '#100f0f'

const primaryColor = '#4ec5ff'
const secondaryColor = '#14eac3'

const appBarColor = '#ec00d9'
const appBarBackgroundColor = backgroundColor


const darkTheme = appTheme(blkOrWhite, backgroundColor, primaryColor, secondaryColor, appBarColor, appBarBackgroundColor)
export default darkTheme
