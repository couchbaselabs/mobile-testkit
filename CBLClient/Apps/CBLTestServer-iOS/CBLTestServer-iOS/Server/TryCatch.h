//
//  TryCatch.h
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 9/17/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

#import <Foundation/Foundation.h>

@interface TryCatch : NSObject

+ (void) tryBlock:(nonnull void (^)(void))tryBlock
       catchBlock:(nullable void (^)(_Nonnull id))catchBlock
     finallyBlock:(nullable void (^)(void))finallyBlock;

@end
