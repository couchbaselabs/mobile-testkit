//
//  CBLTryCatch.m
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 9/17/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

#import "TryCatch.h"

@implementation TryCatch

+ (void) tryBlock:(nonnull void (^)(void))tryBlock
       catchBlock:(nullable void (^)(_Nonnull id))catchBlock
     finallyBlock:(nullable void (^)(void))finallyBlock
{
    @try {
        tryBlock();
    }
    @catch (id exception) {
        if (catchBlock)
            catchBlock(exception);
    }
    @finally {
        if (finallyBlock)
            finallyBlock();
    }
}
@end
