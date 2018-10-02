## Copyright 2015 Jakub Bubnicki
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

#install.packages(c("RCurl", "sp"))
library(RCurl)
library(tcltk)
library(sp)

###########################
# ---- CONFIGURATION ---- #
###########################

config <- list(
    # the address of your Trapper server e.g.
    HOST="https://demo.trapper-project.org",
    # your Trapper login  e.g.
    LOGIN="trapper-project@gmail.com",
    # these urls can change in the future as Trapper is 
    # under active development:
    URLS=list(
        "DEPLOYMENTS"="geomap/api/deployments/export/",
        # "2" at the end of the url below is the classification project id in Trapper
        "RESULTS"="media_classification/api/classifications/results/2/" 
    ),
    # the example of query strings used for simple data filtering
    # try different options e.g. species=Wild+Boar ...
    results.qstring="species=Red+Deer&age=&behaviour=&gender=",
    deployments.qstring="research_project=3&correct_setup=True&correct_tstamp=True"
)

#######################
# ---- FUNCTIONS ---- #
#######################

# the simple GUI to read user's password; based on:
# http://stackoverflow.com/questions/2917202/way-to-securely-give-a-password-to-r-application
getPass <- function() {
    wnd <- tktoplevel()
    tclVar("") -> passVar
    tkgrid(tklabel(wnd, text="Enter password:"))
    tkgrid(tkentry(wnd, textvariable=passVar, show="*") -> passBox)
    tkbind(passBox, "<Return>", function() tkdestroy(wnd))
    tkgrid(tkbutton(wnd, text="OK",command=function() tkdestroy(wnd)))
    tkwait.window(wnd)
    password <- tclvalue(passVar)
    return(password)
}

buildFullUrl <- function(host, page, qstring=NULL) {
    fullurl <- paste(
        sub("/$", "", host), sub("/$", "", page), sep="/"
    )
    if (!is.null(qstring)) fullurl <- paste(fullurl, qstring, sep="/?")
    return(fullurl)
}

getData <- function(host, apiURL, login, qstring=NULL, save2csv=TRUE, csvName="results.csv", curlVerbose=FALSE) {
    # check if your password has already been saved as 'trapper.password' object
    if (!exists("trapper.password")) {
        # get password    
         trapper.password <<- getPass()

    }
    # build url
    cat("Building a full URL...\n")
    url <- buildFullUrl(host, apiURL, qstring)
    cat(paste(url,"\n",sep=""))
    # get data
    cat("Downloading data from the server...\n")
    data <- getURL(
        url, httpauth = 1L,
        userpwd=paste(login, trapper.password, sep=":"),
        verbose=curlVerbose
    )
    df <- read.csv(textConnection(data), sep=",")
    if (save2csv) write.table(df, csvName, sep=",")
    return(df)
}

parseDateTimeColumns <- function(df, columns, format="%Y-%m-%d %H:%M:%S") {
    for (c in columns) {
        df[[c]] <- strptime(df[[c]], format)
    }
    return(df)
}

calculateTrapRates <- function(deployments, results, countVariable, sequenceAggFun=sum) {
    deployments$days <- as.numeric(
        deployments$deployment_end-deployments$deployment_start, units="days"
    )
    # aggregate data step I
    countsI <- setNames(
        aggregate(
            results[, countVariable], by=list(results$deployment_id, results$sequence_id), FUN=sequenceAggFun
        ),
        c("deployment_id", "sequence_id", "count")
    )
    # aggregate data step II
    countsII <- setNames(
        aggregate(
            countsI[, "count"], by=list(countsI$deployment_id), FUN=sum
        ),
        c("deployment_id", "count")
    )
    # merge counts with deployments
    merged <- merge(deployments, countsII, all.x=TRUE, by ="deployment_id")
    merged[is.na(merged$count),]$count <- 0
    merged$trate <- merged$count / merged$days
    return(merged)
}

buildOccupancyMatrix <- function(deployments, results, countVariable, offset=1, returnCounts=False, save2csv=TRUE, minVisits=5) {

    warningMsg <- "[WARNING] Not a valid deployment. Skipping..."
    occu.history <- list()

    # loop over deployments
    for (i in 1:nrow(deployments)) {
        d <- deployments[i,]
        cat(paste(i, "Deployment ID:", d$deployment_id, "\n"))
        valid.deployment <- TRUE
        d.start <- as.Date(d$deployment_start)
        d.end <- as.Date(d$deployment_end)
        d.id <- as.character(d$deployment_id)
        if(is.na(d.start) || is.na(d.end)) {
            print(warningMsg)
            next
        }
        # number of visits (days camera was recording)
        visits <- as.numeric(d.end-d.start, units="days")
        if (!visits || visits <= minVisits) {
            print(warningMsg)
            next
        }
        occu.history[[d.id]] <- rep(0, visits)
        
        # get results/observations for current deployment
        d.data <- results[results$deployment_id == d.id,]
        if (nrow(d.data) == 0) {
            next
        }
        # aggregate data by countVariable
        d.data.agg <- setNames(
            aggregate(
                d.data[, countVariable], by=list(as.Date(d.data$date_recorded)), FUN=sum
            ),
            c("date", "count")
        )
        
        # loop over observations at given deployment
        for (j in 1:nrow(d.data.agg)) {
            observation <- d.data.agg[j,]
            day <- as.numeric(observation$date - d.start, unit="days")
            val <- 1
            if (returnCounts) val <- as.numeric(observation$count)
            if (day > length(occu.history[[d.id]])) {
                valid.deployment <- FALSE
                break
            }
            occu.history[[d.id]][day] <- val
        }
        # apply the offset
        if (valid.deployment) {
            occu.history[[d.id]] <-
                occu.history[[d.id]][offset:length(occu.history[[d.id]])-offset]
        } else {
            print(warningMsg)
            occu.history[[d.id]] <- NULL
        }
    }
    max_length <- max(sapply(occu.history,length))
    df <- sapply(occu.history, function(x){
        c(x, rep(NA, max_length - length(x)))
    })
    if (save2csv) write.table(t(df), "occupancy_matrix.csv", sep=",")
    return(t(df))
}

#############################
# ---- RUN THE EXAMPLE ---- #
#############################

# get classifications
results <- getData(
    config$HOST, config$URLS$RESULTS, config$LOGIN,
    config$results.qstring
)
# get deployments
deployments <- getData(
    config$HOST, config$URLS$DEPLOYMENTS, config$LOGIN,
    config$deployments.qstring, csvName="deployments.csv"
)

# exclude low quality data (e.g. view of a camera blocked by some objects)
deployments <- deployments[!deployments$view_quality=="Exclude",]

# parse datetime values
deployments <- parseDateTimeColumns(
    deployments, c("deployment_start", "deployment_end")
)
results <- parseDateTimeColumns(results, c("date_recorded"))

cat("Calculating trapping rates...\n")
trate <- calculateTrapRates(deployments, results, "number_new")
#trate <- na.omit(trate)
# make spatial object
coordinates(trate) <- ~location_X+location_Y

cat("Building occupancy matrix...\n")
occu.matrix <- buildOccupancyMatrix(
    deployments, results, countVariable="number_new",
    offset=1, returnCounts=FALSE, save2csv=TRUE, minVisits=5
)
cat("Calculating occupancy (naive)...\n")
occu.naive <- rowMeans(occu.matrix, na.rm=TRUE)
occu.df <- as.data.frame(occu.naive)
occu.df$deployment.id <- row.names(occu.df)
# add coordinates
coords <- deployments[c("deployment_id", "location_X", "location_Y")]
occu.naive <- merge(occu.df, coords, by.x="deployment.id", by.y="deployment_id")
# make spatial object
coordinates(occu.naive) <- ~location_X+location_Y

cat("Generating & saving plots...\n")
pdf("bubbles.pdf", paper="a4", width=10, height=10)
# make bubbles - trapping rate
bubble(
    trate, zcol="trate", pch=1, key.entries=c(0, 0.1, 0.2, 0.5, 1),
    sp.layout=list("sp.points", trate, col="grey"), main="Trapping Rate"
)
# make bubbles - naive occupancy
bubble(
    occu.naive, zcol="occu.naive", pch=1, key.entries=c(0, 0.1, 0.2, 0.5, 1),
    sp.layout=list("sp.points", occu.naive, col="grey"), main="Occupancy (naive)"
)
dev.off()

rm(trapper.password)
#save.image()
