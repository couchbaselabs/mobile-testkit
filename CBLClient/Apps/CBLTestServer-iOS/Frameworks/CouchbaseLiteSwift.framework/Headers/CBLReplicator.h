//
//  CBLReplicator.h
//  CouchbaseLite
//
//  Created by Jens Alfke on 3/13/17.
//  Copyright © 2017 Couchbase. All rights reserved.
//

#import <Foundation/Foundation.h>
@class CBLDatabase;
@class CBLReplicatorChange;
@class CBLReplicatorConfiguration;
@protocol CBLListenerToken;

NS_ASSUME_NONNULL_BEGIN


/** Activity level of a replicator. */
typedef enum {
    kCBLReplicatorStopped,    ///< The replicator is finished or hit a fatal error.
    kCBLReplicatorOffline,    ///< The replicator is offline as the remote host is unreachable.
    kCBLReplicatorConnecting, ///< The replicator is connecting to the remote host.
    kCBLReplicatorIdle,       ///< The replicator is inactive waiting for changes or offline.
    kCBLReplicatorBusy        ///< The replicator is actively transferring data.
} CBLReplicatorActivityLevel;


/** 
 Progress of a replicator. If `total` is zero, the progress is indeterminate; otherwise,
 dividing the two will produce a fraction that can be used to draw a progress bar.
 */
typedef struct {
    uint64_t completed; ///< The number of completed changes processed.
    uint64_t total;     ///< The total number of changes to be processed.
} CBLReplicatorProgress;


/** Combined activity level and progress of a replicator. */
@interface CBLReplicatorStatus: NSObject

/** The current activity level. */
@property (readonly, nonatomic) CBLReplicatorActivityLevel activity;

/** The current progress of the replicator. */
@property (readonly, nonatomic) CBLReplicatorProgress progress;

/** The current error of the replicator. */
@property (readonly, nonatomic, nullable) NSError* error;

@end


/** 
 A replicator for replicating document changes between a local database and a target database.
 The replicator can be bidirectional or either push or pull. The replicator can also be one-short
 or continuous. The replicator runs asynchronously, so observe the status property to
 be notified of progress.
 */
@interface CBLReplicator : NSObject

/**
 The replicator's configuration. The returned configuration object is readonly;
 an NSInternalInconsistencyException exception will be thrown if
 the configuration object is modified.
 */
@property (readonly, nonatomic) CBLReplicatorConfiguration* config;

/** The replicator's current status: its activity level and progress. Observable. */
@property (readonly, nonatomic) CBLReplicatorStatus* status;

/** Initializes a replicator with the given configuration. */
- (instancetype) initWithConfig: (CBLReplicatorConfiguration*)config;

/** Not available */
- (instancetype) init NS_UNAVAILABLE;

/** 
 Starts the replicator. This method returns immediately; the replicator runs asynchronously
 and will report its progress throuh the replicator change notification.
 */
- (void) start;

/** 
 Stops a running replicator. This method returns immediately; when the replicator actually
 stops, the replicator will change its status's activity level to `kCBLStopped`
 and the replicator change notification will be notified accordingly.
 */
- (void) stop;

/** 
 Adds a replicator change listener. Changes will be posted on the main queue.
 
 @param listener The listener to post the changes.
 @return An opaque listener token object for removing the listener.
 */
- (id<CBLListenerToken>) addChangeListener: (void (^)(CBLReplicatorChange*))listener;

/**
 Adds a replicator change listener with the dispatch queue on which changes
 will be posted. If the dispatch queue is not specified, the changes will be
 posted on the main queue.
 
 @param queue The dispatch queue.
 @param listener The listener to post changes.
 @return An opaque listener token object for removing the listener.
 */
- (id<CBLListenerToken>) addChangeListenerWithQueue: (nullable dispatch_queue_t)queue
                                           listener: (void (^)(CBLReplicatorChange*))listener;

/** 
 Removes a change listener with the given listener token.
 
 @param token The listener token;
 */
- (void) removeChangeListenerWithToken: (id<CBLListenerToken>)token;

@end


NS_ASSUME_NONNULL_END
